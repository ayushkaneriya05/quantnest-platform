import threading
import time
import logging
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

class TickCache:
    """
    L1 In-Memory Cache Singleton (Zero-DB Hot Path)
    
    This holds the absolute state required to evaluate ticks without hitting PostgreSQL.
    It runs a background daemon thread that refreshes state every few seconds.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TickCache, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self._sync_lock = threading.Lock()
        self._running = False
        self._thread = None
        
        # In-Memory State Dictionaries
        self.active_paper_strategies = {}  # symbol -> list of dicts {"strategy": obj, "config": dict}
        self.active_live_sessions = {}     # symbol -> list of session objects
        self.terminal_open_orders = {}     # symbol -> list of order objects
        self.paper_open_orders = {}        # symbol -> list of PaperOrder objects
        
        self.paper_positions = {}          # (strategy_id, instrument_id) -> position object
        self.paper_stats = {}              # strategy_id -> dict of daily trades
        self.paper_accounts = {}           # strategy_id -> PaperAccount object
        
        self.live_positions = {}           # (session_id, instrument_id) -> position object
        self.live_stats = {}               # session_id -> dict of daily trades
        self.live_open_orders = {}         # session_id -> list of LiveOrder objects
        self.live_allocations = {}         # session_id -> allocation object
        self.instruments = {}              # symbol -> instrument object

        self.watchlists = {}               # (strategy_id, instrument_id) -> watch object
        
        # Last sync time
        self.last_sync = None

    def start_background_sync(self, interval_seconds=3):
        with self._sync_lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._sync_loop, 
                args=(interval_seconds,), 
                daemon=True,
                name="L1CacheSyncThread"
            )
            self._thread.start()
            logger.info("TickCache background sync started.")

    def stop_background_sync(self):
        with self._sync_lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=2)
                self._thread = None

    def _sync_loop(self, interval_seconds):
        while self._running:
            try:
                self.force_sync()
            except Exception as e:
                logger.error("TickCache background sync failed: %s", e)
            finally:
                from django.db import connection
                connection.close()  # Force Django to close the connection to avoid stale reads
            time.sleep(interval_seconds)

    def force_sync(self):
        """Pulls all required state from DB into memory dictionaries."""
        try:
            self._sync_terminal_orders()
            self._sync_paper_strategies()
            self._sync_live_sessions()
            self.last_sync = timezone.now()
        except Exception as e:
            logger.error("Error in TickCache force_sync: %s", e)

    def _sync_terminal_orders(self):
        from trading.models import Order
        open_orders = Order.objects.filter(status="OPEN").select_related("account", "instrument")
        new_cache = {}
        for order in open_orders:
            sym = order.instrument.sym_ticker
            if sym not in new_cache:
                new_cache[sym] = []
            new_cache[sym].append(order)
        self.terminal_open_orders = new_cache

    def _sync_paper_strategies(self):
        from strategies.models import Strategy
        from common.enums import StrategyStatus
        from paper_trading.models import PaperPosition, PaperTrade, PaperOrder
        
        strategies = Strategy.objects.filter(
            paper_trading_enabled=True,
            status=StrategyStatus.ACTIVE,
            capital_allocation__is_active=True
        ).prefetch_related("watchlist_instruments__instrument")
        
        new_strategies = {}
        new_positions = {}
        new_stats = {}
        new_accounts = {}
        
        today = timezone.localdate()
        
        for strategy in strategies:
            config = strategy.to_execution_dict()
            strat_id = strategy.id
            
            # Watchlists
            for watch in strategy.watchlist_instruments.all():
                sym = watch.instrument.sym_ticker
                if sym not in new_strategies:
                    new_strategies[sym] = []
                new_strategies[sym].append({"strategy": strategy, "config": config})
                self.watchlists[(strat_id, watch.instrument.id)] = watch
                self.instruments[sym] = watch.instrument
            
            # Stats (Daily Trades)
            trades_today = PaperTrade.objects.filter(strategy=strategy, exit_time__date=today).count()
            latest_exit = PaperTrade.objects.filter(strategy=strategy).order_by("-exit_time").first()
            new_stats[strat_id] = {
                "daily_trades": trades_today,
                "instrument_daily_trades": trades_today, # Simplified for now
                "last_exit_time": latest_exit.exit_time if latest_exit else None,
                "last_entry_time": None # Simplified for now
            }
        
        # Positions
        positions = PaperPosition.objects.filter(strategy__in=strategies).select_related("instrument")
        for pos in positions:
            key = (pos.strategy_id, pos.instrument_id)
            new_positions[key] = pos

        from paper_trading.services import PaperExecutionService
        # Open Orders
        open_orders = PaperOrder.objects.filter(
            strategy__in=strategies,
            status__in=PaperExecutionService.STRATEGY_ORDER_STATUSES
        ).select_related("instrument")
        
        new_open_orders = {}
        for o in open_orders:
            sym = o.instrument.sym_ticker
            if sym not in new_open_orders:
                new_open_orders[sym] = []
            new_open_orders[sym].append(o)
            
        # Accounts
        from paper_trading.models import PaperAccount
        accounts = PaperAccount.objects.filter(allocation__strategy__in=strategies)
        for acc in accounts:
            new_accounts[acc.allocation.strategy_id] = acc
            
        self.active_paper_strategies = new_strategies
        self.paper_stats = new_stats
        self.paper_positions = new_positions
        self.paper_open_orders = new_open_orders
        self.paper_accounts = new_accounts

    def _sync_live_sessions(self):
        from live_trading.models import LivePosition, LiveOrder, TradingSession, LiveStrategyAllocation
        from common.enums import StrategyStatus
        
        sessions = TradingSession.objects.filter(
            status="RUNNING", 
            strategy__status=StrategyStatus.ACTIVE
        ).select_related("strategy", "broker_credential")
        
        new_sessions = {}
        new_positions = {}
        new_stats = {}
        new_allocations = {}
        today = timezone.localdate()

        from live_trading.services import LiveExecutionService
        for session in sessions:
            for watch in session.strategy.watchlist_instruments.all():
                sym = watch.instrument.sym_ticker
                if sym not in new_sessions:
                    new_sessions[sym] = []
                new_sessions[sym].append(session)
                self.watchlists[(session.strategy_id, watch.instrument.id)] = watch
                self.instruments[sym] = watch.instrument
            
            # Stats
            trades_today = LiveOrder.objects.filter(
                session=session, 
                executed_at__date=today,
                status__in=LiveExecutionService.FILLED_ORDER_STATUSES
            ).count()
            latest_exit = LiveOrder.objects.filter(
                session=session, status__in=LiveExecutionService.FILLED_ORDER_STATUSES
            ).exclude(executed_at__isnull=True).order_by("-executed_at").first()
            
            new_stats[session.id] = {
                "daily_trades": trades_today,
                "instrument_daily_trades": trades_today,
                "last_exit_time": latest_exit.executed_at if latest_exit else None,
                "last_entry_time": None
            }
            
            # Allocation
            allocation = LiveStrategyAllocation.objects.filter(
                user=session.user_id,
                strategy=session.strategy_id,
                broker_credential=session.broker_credential_id,
                is_active=True,
            ).first()
            new_allocations[session.id] = allocation

        # Positions
        session_map = {
            (s.user_id, s.strategy_id, s.broker_credential_id): s.id 
            for s in sessions
        }
        
        if sessions:
            from django.db.models import Q
            q_objects = Q()
            for s in sessions:
                q_objects |= Q(user_id=s.user_id, strategy_id=s.strategy_id, broker_credential_id=s.broker_credential_id)
            
            positions = LivePosition.objects.filter(q_objects).select_related("instrument")
            for pos in positions:
                s_id = session_map.get((pos.user_id, pos.strategy_id, pos.broker_credential_id))
                if s_id:
                    key = (s_id, pos.instrument_id)
                    new_positions[key] = pos

        # Open Orders
        open_orders = LiveOrder.objects.filter(
            session__in=sessions,
            status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES
        )
        new_open_orders = {}
        for o in open_orders:
            if o.session_id not in new_open_orders:
                new_open_orders[o.session_id] = []
            new_open_orders[o.session_id].append(o)

        self.active_live_sessions = new_sessions
        self.live_positions = new_positions
        self.live_stats = new_stats
        self.live_open_orders = new_open_orders
        self.live_allocations = new_allocations

    # --- Fast Memory Accessors ---

    def get_terminal_orders(self, symbol):
        return self.terminal_open_orders.get(symbol, [])

    def get_paper_open_orders(self, symbol):
        return self.paper_open_orders.get(symbol, [])

    def get_paper_account(self, strategy_id):
        return self.paper_accounts.get(strategy_id)

    def get_paper_strategies(self, symbol):
        return self.active_paper_strategies.get(symbol, [])
        
    def get_paper_position(self, strategy_id, instrument_id):
        return self.paper_positions.get((strategy_id, instrument_id))
        
    def get_paper_stats(self, strategy_id):
        return self.paper_stats.get(strategy_id, {
            "daily_trades": 0, 
            "instrument_daily_trades": 0,
            "last_exit_time": None,
            "last_entry_time": None
        })

    def get_live_sessions(self, symbol):
        return self.active_live_sessions.get(symbol, [])

    def get_live_position(self, session_id, instrument_id):
        return self.live_positions.get((session_id, instrument_id))

    def get_live_open_orders(self, session_id):
        return self.live_open_orders.get(session_id, [])

    def get_live_allocation(self, session_id):
        return self.live_allocations.get(session_id)

    def get_live_stats(self, session_id):
        return self.live_stats.get(session_id, {
            "daily_trades": 0, 
            "instrument_daily_trades": 0,
            "last_exit_time": None,
            "last_entry_time": None
        })

    def get_instrument(self, symbol):
        return self.instruments.get(symbol)

    def get_watchlist_instrument(self, strategy_id, instrument_id):
        return self.watchlists.get((strategy_id, instrument_id))

# Expose global instance
tick_cache = TickCache()
