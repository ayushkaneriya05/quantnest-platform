import logging
import time
import concurrent.futures
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache
from instruments.models import Instrument
from common.enums import InstrumentType
from .streaming import MarketDataStreamer
from .utils import get_active_fyers_access_token


try:
    from fyers_apiv3.FyersWebsocket import data_ws
except Exception: 
    data_ws = None

logger = logging.getLogger(__name__)


class LiveMarketDataRegistry:
    cache_key = "marketdata:tracked_symbols"
    client_cache_key = "marketdata:client_subscription_counts"
    cache_ttl = 60 * 60 * 6

    @classmethod
    def get_symbols(cls):
        return sorted(set(cache.get(cls.cache_key, [])))

    @classmethod
    def set_symbols(cls, symbols):
        normalized = sorted({
            MarketDataStreamer.normalize_symbol(symbol) for symbol in (symbols or []) if symbol
        })
        cache.set(cls.cache_key, normalized, timeout=cls.cache_ttl)
        return normalized


    @classmethod
    def add_symbols(cls, symbols):
        return cls.set_symbols([*cls.get_symbols(), *(symbols or [])])


    @classmethod
    def get_client_subscription_counts(cls):
        return dict(cache.get(cls.client_cache_key, {}) or {})


    @classmethod
    def get_client_symbols(cls):
        counts = cls.get_client_subscription_counts()
        return sorted(symbol for symbol, count in counts.items() if int(count or 0) > 0)


    @classmethod
    def add_client_subscription(cls, symbol):
        normalized = MarketDataStreamer.normalize_symbol(symbol)
        counts = cls.get_client_subscription_counts()
        counts[normalized] = int(counts.get(normalized, 0) or 0) + 1
        cache.set(cls.client_cache_key, counts, timeout=cls.cache_ttl)
        return cls.set_symbols([*cls.get_symbols(), normalized])

    @classmethod
    def remove_client_subscription(cls, symbol):
        normalized = MarketDataStreamer.normalize_symbol(symbol)
        counts = cls.get_client_subscription_counts()
        next_count = int(counts.get(normalized, 0) or 0) - 1
        if next_count > 0:
            counts[normalized] = next_count
        else:
            counts.pop(normalized, None)
        cache.set(cls.client_cache_key, counts, timeout=cls.cache_ttl)
       
        return cls.get_symbols()

    @classmethod
    def refresh_from_active_accounts(cls):
        from paper_trading.models import PaperAccount, PaperOrder, PaperPosition
        from common.enums import StrategyStatus
        from live_trading.models import LiveOrder, LivePosition, TradingSession
        from strategies.models import Strategy
        from trading.models import Order, Position

        tracked = set()
        tracked.update(cls.get_client_symbols())

        # Legacy/Strategy Paper Trading
        open_position_symbols = PaperPosition.objects.filter(
            account__sessions__status__in=["RUNNING", "PAUSED"],
            account__user__isnull=False,
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in open_position_symbols if symbol)

        pending_order_symbols = PaperOrder.objects.filter(
            account__sessions__status__in=["RUNNING", "PAUSED"],
            account__user__isnull=False,
            status__in=["PENDING", "PLACED", "PARTIAL_FILL"],
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in pending_order_symbols if symbol)

        # New Dashboard Trading Terminal
        dashboard_positions = Position.objects.values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in dashboard_positions if symbol)

        dashboard_orders = Order.objects.filter(status="OPEN").values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in dashboard_orders if symbol)

        active_accounts = (
            PaperAccount.objects.filter(sessions__status__in=["RUNNING", "PAUSED"], user__isnull=False)
            .prefetch_related("orders__instrument", "positions__instrument")
        )
        for account in active_accounts:
            for position in account.positions.all():
                if position.instrument and position.instrument.sym_ticker:
                    tracked.add(position.instrument.sym_ticker)
            for order in account.orders.all():
                if order.instrument and order.instrument.sym_ticker and order.status in {"PENDING", "PLACED", "PARTIAL_FILL"}:
                    tracked.add(order.instrument.sym_ticker)

        paper_strategies = (
            Strategy.objects.filter(
                paper_trading_enabled=True,
                status=StrategyStatus.ACTIVE,
                paper_sessions__status="RUNNING"
            )
            .prefetch_related(
                "watchlist_instruments__instrument",
                "watchlist_instruments__execution_routes__target_instrument",
                "watchlist_instruments__execution_routes__target_underlying_instrument",
            )
            .distinct()
        )
        for strategy in paper_strategies:
            for watch in strategy.watchlist_instruments.all():
                if watch.instrument and watch.instrument.sym_ticker:
                    tracked.add(watch.instrument.sym_ticker)
                # for route in watch.execution_routes.all():
                #     if route.target_instrument and route.target_instrument.sym_ticker:
                #         tracked.add(route.target_instrument.sym_ticker)
                #     if route.target_underlying_instrument:
                #         tracked.add(route.target_underlying_instrument.sym_ticker)
                #     if route.route_type in {"FUTURES", "OPTIONS"}:
                #         candidates = Instrument.objects.filter(
                #             instrument_type=InstrumentType.FUTURE if route.route_type == "FUTURES" else InstrumentType.OPTION,
                #             underlying_symbol=(
                #                 route.target_underlying_instrument.symbol
                #                 if route.target_underlying_instrument_id
                #                 else watch.instrument.symbol
                #             ),
                #             is_active=True,
                #             is_tradeable=True,
                #         ).values_list("sym_ticker", flat=True)
                #         tracked.update(symbol for symbol in candidates if symbol)

        live_position_symbols = LivePosition.objects.filter(
            user__isnull=False,
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in live_position_symbols if symbol)

        live_pending_symbols = LiveOrder.objects.filter(
            user__isnull=False,
            status__in=["PENDING", "PLACED", "PARTIAL_FILL"],
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in live_pending_symbols if symbol)

        live_sessions = (
            TradingSession.objects.filter(
                status="RUNNING",
                strategy__live_trading_enabled=True,
                strategy__status=StrategyStatus.ACTIVE,
            )
            .prefetch_related(
                "strategy__watchlist_instruments__instrument",
                "strategy__watchlist_instruments__execution_routes__target_instrument",
                "strategy__watchlist_instruments__execution_routes__target_underlying_instrument",
            )
            .distinct()
        )
        for session in live_sessions:
            for watch in session.strategy.watchlist_instruments.all():
                if watch.instrument and watch.instrument.sym_ticker:
                    tracked.add(watch.instrument.sym_ticker)
                # for route in watch.execution_routes.all():
                #     if route.target_instrument and route.target_instrument.sym_ticker:
                #         tracked.add(route.target_instrument.sym_ticker)
                #     if route.target_underlying_instrument:
                #         tracked.add(route.target_underlying_instrument.sym_ticker)
                #     if route.route_type in {"FUTURES", "OPTIONS"}:
                #         candidates = Instrument.objects.filter(
                #             instrument_type=InstrumentType.FUTURE if route.route_type == "FUTURES" else InstrumentType.OPTION,
                #             underlying_symbol=(
                #                 route.target_underlying_instrument.symbol
                #                 if route.target_underlying_instrument_id
                #                 else watch.instrument.symbol
                #             ),
                #             is_active=True,
                #             is_tradeable=True,
                #         ).values_list("sym_ticker", flat=True)
                #         tracked.update(symbol for symbol in candidates if symbol)

        if not tracked:
            return cls.set_symbols([])

        active_tracked = Instrument.objects.filter(
            sym_ticker__in=tracked,
            is_active=True,
            is_tradeable=True
        ).values_list('sym_ticker', flat=True)

        return cls.set_symbols(list(active_tracked))


class FyersLiveFeedClient:
    def __init__(self):
        self.socket = None
        self._subscribed_symbols = set()
        self._invalid_symbols = set()
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=50, thread_name_prefix="tick_worker")
        self.last_candle_updates = {}
        self.shm_managers = {}


    def connect(self):
        if data_ws is None:
            raise RuntimeError("fyers_apiv3 websocket client is not available")

        client_id = getattr(settings, "FYERS_CLIENT_ID", "")
        access_token = get_active_fyers_access_token()
        if not client_id or not access_token:
            raise RuntimeError("Valid Fyers websocket credentials are not available")

        self.socket = data_ws.FyersDataSocket(
            access_token=f"{client_id}:{access_token}",
            log_path=str(settings.BASE_DIR / "logs"),
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_connect=self._on_connect,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
        )
        self.socket.connect()
        
        
        return self.socket


    def sync_subscriptions(self, force=False):
        if self.socket is None:
            return []

        target_symbols = set(LiveMarketDataRegistry.refresh_from_active_accounts())
        target_symbols -= self._invalid_symbols
        additions = target_symbols if force else target_symbols - self._subscribed_symbols
        removals = set() if force else self._subscribed_symbols - target_symbols

        if additions:
            for sym in sorted(additions):
                self.socket.subscribe(symbols=[sym], data_type="SymbolUpdate")
                if sym not in self.shm_managers:
                    from marketdata.shared_memory import SharedMemoryManager
                    try:
                        # Fetch the max lookback dynamically from deployed configs
                        max_lookback = 200 
                        try:
                            from live_trading.models import TradingSession
                            from paper_trading.models import PaperTradingSession
                            from rules_engine.metadata import IndicatorRequirementAnalyzer
                            
                            tf_max_lookbacks = {"1m": 200}

                            def update_lookbacks(sessions):
                                for session in sessions:
                                    if session.allocation and session.allocation.deployed_version:
                                        warmup = IndicatorRequirementAnalyzer.get_warmup_requirements(session.allocation.deployed_version.config_snapshot)
                                        for tf, req_len in warmup.items():
                                            if tf not in tf_max_lookbacks or req_len > tf_max_lookbacks[tf]:
                                                tf_max_lookbacks[tf] = req_len

                            active_live = TradingSession.objects.filter(
                                status__in=["RUNNING", "PAUSED"], 
                                allocation__strategy__watchlist_instruments__instrument__sym_ticker=sym
                            ).select_related('allocation__deployed_version').distinct()
                            
                            update_lookbacks(active_live)
                            
                            active_paper = PaperTradingSession.objects.filter(
                                status__in=["RUNNING", "PAUSED"], 
                                allocation__strategy__watchlist_instruments__instrument__sym_ticker=sym
                            ).select_related('allocation__deployed_version').distinct()
                            
                            update_lookbacks(active_paper)
                                    
                            # Determine total 1m candles needed to satisfy the max timeframe requirement
                            tf_mins = {"1m": 1, "3m": 3, "5m": 5, "10m": 10, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1D": 375, "1W": 1875}
                            total_1m_needed = [req_len * tf_mins.get(tf, 1) for tf, req_len in tf_max_lookbacks.items()]
                            if total_1m_needed:
                                max_lookback = max(total_1m_needed)
                        except Exception as elookback:
                            logger.error(f"Error calculating lookback for {sym}: {elookback}")
                            max_lookback = 250
                            
                        # Ensure SHM size can accommodate the max_lookback + safety buffer
                        shm_size = max(10000, max_lookback + 500)
                        
                        self.shm_managers[sym] = SharedMemoryManager(sym, "1m", max_size=shm_size, create=True)
                        self.shm_managers[sym].preload_historical_data(max_lookback)
                    except Exception as e:
                        logger.error("Failed to init SHM for %s: %s", sym, e)
            logger.info("Subscribed live feed to %s symbol(s) individually", len(additions))

        if removals and hasattr(self.socket, "unsubscribe"):
            for sym in sorted(removals):
                self.socket.unsubscribe(symbols=[sym], data_type="SymbolUpdate")
            logger.info("Unsubscribed live feed from %s symbol(s) individually", len(removals))

        self._subscribed_symbols = target_symbols
        return sorted(target_symbols)


    def shutdown(self):
        logger.info("Shutting down Fyers live feed threadpool...")
        self.thread_pool.shutdown(wait=True)


    def _on_connect(self):
        logger.info("Connected to Fyers live market websocket")
        self.sync_subscriptions(force=True)


    def _on_close(cls, ws=None, code=None, reason=None):
        logger.info(f"Fyers WebSocket connection closed. Code: {code}, Reason: {reason}")
        if cls.socket and getattr(cls.socket, "reconnect", False):
            pass
        # Notify users with active live sessions about feed disconnection
        from django.core.cache import cache
        throttle_key = "market_feed_disconnect_notification"
        if not cache.get(throttle_key):
            try:
                from live_trading.models import TradingSession
                from notifications.services import NotificationService
                from common.enums import NotificationType, Severity
                notified_users = set()
                for session in TradingSession.objects.filter(status="RUNNING").select_related("user"):
                    if session.user_id not in notified_users:
                        NotificationService.notify(
                            user=session.user,
                            title="Market Data Feed Disconnected",
                            message="Live market data feed has disconnected. Strategies may not receive real-time quotes until reconnection.",
                            notification_type=NotificationType.SYSTEM_ALERT,
                            severity=Severity.CRITICAL,
                            data={"module": "marketdata", "close_code": str(code)}
                        )
                        notified_users.add(session.user_id)
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Failed dispatching market feed disconnect notification")
            cache.set(throttle_key, True, 600)  # 10 min throttle


    def _on_error(self, message):
        logger.error("Fyers live websocket error: %s", message)
        if isinstance(message, dict):
            if message.get("code") == -99:
                logger.info("Refreshing Fyers websocket token after expiry")
                try:
                    self.connect()
                except Exception as exc:  # pragma: no cover - reconnect safety
                    logger.exception("Failed reconnecting Fyers websocket: %s", exc)
            elif message.get("code") == -300 and "invalid_symbols" in message:
                invalid_symbols = message.get("invalid_symbols", [])
                logger.warning("Fyers marked symbols as invalid: %s", invalid_symbols)
                self._invalid_symbols.update(invalid_symbols)
                self._subscribed_symbols -= set(invalid_symbols)


    def _on_message(self, message):
        # Fyers V3 can send a single dict or a list of dicts
        ticks = message if isinstance(message, list) else [message]
        
        for tick in ticks:
            if not isinstance(tick, dict):
                continue
                
            symbol = tick.get("symbol")
            if not symbol or isinstance(symbol, list):
                continue
                
            ltp = tick.get("ltp")
            if ltp in (None, "", 0, "0"):
                continue

            traded_at = tick.get("last_traded_time")
            traded_at_dt = (
                datetime.fromtimestamp(traded_at, tz=timezone.utc)
                if traded_at
                else datetime.now(timezone.utc)
            )

            quote = {
                "price": ltp,
                
                # Backward compatibility for existing backend engines and frontend components
                "open": tick.get("open_price"),
                "high": tick.get("high_price"),
                "low": tick.get("low_price"),
                "close": tick.get("prev_close_price"),
                
                # New, accurate Fyers Daily keys
                "day_open": tick.get("open_price"),
                "day_high": tick.get("high_price"),
                "day_low": tick.get("low_price"),
                "prev_close": tick.get("prev_close_price"),
                "change": tick.get("ch"),
                "change_percent": tick.get("chp"),
                "volume": tick.get("vol_traded_today"),
                "last_traded_qty": tick.get("last_traded_qty"),
                "avg_trade_price": tick.get("avg_trade_price"),
                "timestamp": traded_at_dt.isoformat(),
            }


            # Write to ultra-fast POSIX shared memory for Execution V2
            if symbol in self.shm_managers:
                try:
                    self.shm_managers[symbol].update_current_candle(
                        price=float(quote["price"]),
                        volume=float(quote["volume"] or 0),
                        timestamp=traded_at_dt.timestamp(),
                    )
                except Exception as exc:
                    logger.error("SHM write failed for %s: %s", symbol, exc)

            def _dispatch_terminal():
                try:
                    from trading.services import TradingOrderService, TerminalOrderCache
                    open_orders = TerminalOrderCache.get_terminal_orders(symbol)
                    if open_orders:
                        TradingOrderService.process_matching_engine(symbol, quote, open_orders=open_orders)
                except Exception as exc:
                    logger.exception("Terminal matching error for %s: %s", symbol, exc)

            try:
                # Broadcast to frontend websockets via Django Channels
                MarketDataStreamer.publish_tick(symbol, quote)
                
                # Terminal manual trading matching engine
                self.thread_pool.submit(_dispatch_terminal)
                
                # The Execution V2 engine (multiprocessing Actor loop) reads directly from Shared Memory.
            except Exception as exc:
                logger.exception("Failed executing threadpool dispatch for %s: %s", symbol, exc)
