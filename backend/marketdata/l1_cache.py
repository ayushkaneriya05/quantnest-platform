import threading
import time
import logging
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
        self.terminal_open_orders = {}     # symbol -> list of order objects
        self.paper_open_orders = {}        # symbol -> list of PaperOrder objects
        
        self.paper_accounts = {}           # strategy_id -> PaperAccount object
        
        self.live_open_orders = {}         # session_id -> list of LiveOrder objects
        self.live_allocations = {}         # session_id -> allocation object
        # Last sync time
        self.last_sync = None

    def start_background_sync(self, interval_seconds=1):
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
        from paper_trading.models import PaperPosition, PaperTrade, PaperOrder, PaperTradingSession
        
        sessions = PaperTradingSession.objects.filter(
            status__in=["RUNNING", "PAUSED"]
        ).select_related(
            "strategy", "allocation", "account", "allocation__deployed_version"
        ).prefetch_related(
            "strategy__watchlist_instruments__instrument"
        ).distinct()
        
        new_accounts = {}
        
        today = timezone.localdate()
        active_strategies = []
        
        for session in sessions:
            strategy = session.strategy
            sess_id = session.id
            strat_id = strategy.id
            active_strategies.append(strategy)
            
            new_accounts[sess_id] = session.account
        
        from paper_trading.services import PaperExecutionService
        # Open Orders
        open_orders = PaperOrder.objects.filter(
            strategy__in=active_strategies,
            status__in=PaperExecutionService.STRATEGY_ORDER_STATUSES
        ).select_related("instrument")
        
        new_open_orders = {}
        for o in open_orders:
            sym = o.instrument.sym_ticker
            if sym not in new_open_orders:
                new_open_orders[sym] = []
            new_open_orders[sym].append(o)
            
        self.paper_open_orders = new_open_orders
        self.paper_accounts = new_accounts

    def _sync_live_sessions(self):
        from live_trading.models import LiveOrder, TradingSession
        from common.enums import StrategyStatus
        
        sessions = TradingSession.objects.filter(
            status="RUNNING", 
            strategy__status=StrategyStatus.ACTIVE
        ).select_related("strategy", "broker_credential", "allocation__deployed_version", "allocation__broker_credential")
        
        new_allocations = {}

        from live_trading.services import LiveExecutionService
        for session in sessions:
            new_allocations[session.id] = session.allocation

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

        self.live_open_orders = new_open_orders
        self.live_allocations = new_allocations

    # --- Fast Memory Accessors ---

    def get_terminal_orders(self, symbol):
        return self.terminal_open_orders.get(symbol, [])


    def get_paper_open_orders(self, symbol):
        return self.paper_open_orders.get(symbol, [])


    def get_paper_account(self, session_id):
        return self.paper_accounts.get(session_id)


    def get_live_open_orders(self, session_id):
        return self.live_open_orders.get(session_id, [])


    def get_live_allocation(self, session_id):
        return self.live_allocations.get(session_id)




# Expose global instance
tick_cache = TickCache()
