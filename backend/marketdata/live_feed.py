import logging
import time
import threading
import concurrent.futures
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache
from instruments.models import Instrument
from .services import MarketDataService
from .streaming import MarketDataStreamer
from .utils import get_active_fyers_access_token


try:
    from fyers_apiv3.FyersWebsocket import data_ws
except Exception: 
    data_ws = None

logger = logging.getLogger(__name__)


class LiveMarketDataRegistry:
    cache_key = "marketdata:tracked_symbols"
    execution_symbols_cache_key = "marketdata:execution_symbols"
    requirements_cache_key = "marketdata:required_lookbacks"
    readiness_cache_key = "marketdata:readiness"
    heartbeat_cache_key = "marketdata:feed_heartbeat"
    client_cache_key = "marketdata:client_subscription_counts"
    cache_ttl = 60 * 60 * 6

    @classmethod
    def get_symbols(cls):
        return sorted(set(cache.get(cls.cache_key, [])))

    @classmethod
    def set_symbols(cls, symbols):
        normalized = sorted({
            MarketDataService.normalize_symbol(symbol) for symbol in (symbols or []) if symbol
        })
        cache.set(cls.cache_key, normalized, timeout=cls.cache_ttl)
        return normalized

    @classmethod
    def get_required_lookbacks(cls):
        return dict(cache.get(cls.requirements_cache_key, {}) or {})

    @classmethod
    def get_execution_symbols(cls):
        return set(cache.get(cls.execution_symbols_cache_key, []) or [])

    @classmethod
    def set_readiness(cls, symbol, required, ready, details=None):
        readiness = dict(cache.get(cls.readiness_cache_key, {}) or {})
        readiness[f"{MarketDataService.normalize_symbol(symbol)}:{int(required)}"] = {
            "ready": bool(ready),
            "details": details or {},
            "updated_at": time.time(),
        }
        cache.set(cls.readiness_cache_key, readiness, timeout=cls.cache_ttl)

    @classmethod
    def clear_readiness(cls, symbol):
        normalized = MarketDataService.normalize_symbol(symbol)
        readiness = dict(cache.get(cls.readiness_cache_key, {}) or {})
        for key in list(readiness):
            if key.rsplit(":", 1)[0] == normalized:
                readiness.pop(key, None)
        cache.set(cls.readiness_cache_key, readiness, timeout=cls.cache_ttl)

    @classmethod
    def is_ready(cls, symbol, required):
        if not cls.is_tick_fresh(symbol):
            return False
        readiness = dict(cache.get(cls.readiness_cache_key, {}) or {})
        normalized = MarketDataService.normalize_symbol(symbol)
        for key, value in readiness.items():
            key_symbol, _, key_depth = key.rpartition(":")
            if key_symbol == normalized and int(key_depth or 0) >= int(required):
                if value.get("ready"):
                    return True
        return False

    @classmethod
    def record_tick(cls, symbol, timestamp=None):
        normalized = MarketDataService.normalize_symbol(symbol)
        cache.set(f"marketdata:last_tick:{normalized}", float(timestamp or time.time()), timeout=cls.cache_ttl)

    @classmethod
    def is_tick_fresh(cls, symbol, max_age=15):
        normalized = MarketDataService.normalize_symbol(symbol)
        tick_at = cache.get(f"marketdata:last_tick:{normalized}")
        return tick_at is not None and 0 <= time.time() - float(tick_at) <= max_age


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
        normalized = MarketDataService.normalize_symbol(symbol)
        counts = cls.get_client_subscription_counts()
        counts[normalized] = int(counts.get(normalized, 0) or 0) + 1
        cache.set(cls.client_cache_key, counts, timeout=cls.cache_ttl)
        return cls.set_symbols([*cls.get_symbols(), normalized])

    @classmethod
    def remove_client_subscription(cls, symbol):
        normalized = MarketDataService.normalize_symbol(symbol)
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
        from paper_trading.models import PaperTradingSession
        from live_trading.models import TradingSession
        from trading.models import Order, Position
        from marketdata.services import MarketDataService

        tracked = set()
        execution_symbols = set()
        required_lookbacks = {}
        tracked.update(cls.get_client_symbols())

        def add_session_requirements(sessions):
            for session in sessions:
                config = {}
                if session.allocation and session.allocation.deployed_version:
                    config = session.allocation.deployed_version.config_snapshot or {}
                watchlist_ids = [
                    item.get("instrument_id") for item in config.get("watchlist_instruments", []) if item.get("instrument_id") is not None
                ]

                instruments = Instrument.objects.filter(id__in=watchlist_ids, is_active=True, is_tradeable=True).values_list("sym_ticker", flat=True)

                required = MarketDataService.required_1m_candles(config) if config else 200
                for symbol in instruments:
                    if symbol:
                        tracked.add(symbol)
                        execution_symbols.add(symbol)
                        required_lookbacks[symbol] = max(required_lookbacks.get(symbol, 0), required)

        # Trading Terminal
        dashboard_positions = Position.objects.values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in dashboard_positions if symbol)

        dashboard_orders = Order.objects.filter(status="OPEN").values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in dashboard_orders if symbol)

        paper_sessions = PaperTradingSession.objects.filter(status__in=["RUNNING", "PAUSED", "ERROR"]).select_related("strategy", "allocation__deployed_version")
        add_session_requirements(paper_sessions)

        live_sessions = TradingSession.objects.filter(status__in=["RUNNING", "PAUSED", "ERROR"],).select_related("strategy", "allocation__deployed_version")
        add_session_requirements(live_sessions)

        cache.set(cls.execution_symbols_cache_key, sorted(MarketDataService.normalize_symbol(symbol) for symbol in execution_symbols), timeout=cls.cache_ttl)

        required_lookbacks = {
            MarketDataService.normalize_symbol(symbol): depth for symbol, depth in required_lookbacks.items()
        }

        cache.set(cls.requirements_cache_key, required_lookbacks, timeout=cls.cache_ttl)

        if not tracked:
            return cls.set_symbols([])

        active_tracked = Instrument.objects.filter(sym_ticker__in=tracked, is_active=True, is_tradeable=True).values_list('sym_ticker', flat=True)

        return cls.set_symbols(list(active_tracked))

class FyersLiveFeedClient:
    def __init__(self):
        self.socket = None
        self._subscribed_symbols = set()
        self._invalid_symbols = set()
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=50, thread_name_prefix="tick_worker")
        self.last_candle_updates = {}
        self.shm_managers = {}
        self._shm_locks = {}
        self._shm_registry_lock = threading.RLock()
        self._sync_thread = None
        self._sync_stop = threading.Event()
        self._sync_wakeup = threading.Event()
        self._volume_lock = threading.Lock()
        self._last_cumulative_volume = {}
        self._last_health_publish = {}


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


    def start_subscription_sync(self, interval=15):
        """Run subscription/history reconciliation off the websocket callback thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            return

        def loop():
            while not self._sync_stop.is_set():
                try:
                    self.sync_subscriptions()
                except Exception:
                    logger.exception("Subscription reconciliation failed")
                self._sync_wakeup.wait(interval)
                self._sync_wakeup.clear()

        self._sync_thread = threading.Thread(
            target=loop,
            name="market-subscription-sync",
            daemon=True,
        )
        self._sync_thread.start()


    def _get_shm_entry(self, symbol):
        with self._shm_registry_lock:
            return self.shm_managers.get(symbol), self._shm_locks.setdefault(symbol, threading.RLock())


    def sync_subscriptions(self, force=False):
        if self.socket is None:
            return []

        cache.set(LiveMarketDataRegistry.heartbeat_cache_key, time.time(), timeout=60)
        target_symbols = set(LiveMarketDataRegistry.refresh_from_active_accounts())
        target_symbols -= self._invalid_symbols
        execution_symbols = LiveMarketDataRegistry.get_execution_symbols() - self._invalid_symbols
        additions = target_symbols if force else target_symbols - self._subscribed_symbols
        removals = set() if force else self._subscribed_symbols - target_symbols

        for sym in sorted(additions):
            self.socket.subscribe(symbols=[sym], data_type="SymbolUpdate")

        required_lookbacks = LiveMarketDataRegistry.get_required_lookbacks()
        from marketdata.shared_memory import SharedMemoryManager
        for symbol in set(self.shm_managers) - execution_symbols:
            shm, symbol_lock = self._get_shm_entry(symbol)
            with symbol_lock:
                if shm is not None:
                    shm.close()
                with self._shm_registry_lock:
                    self.shm_managers.pop(symbol, None)
                    self._shm_locks.pop(symbol, None)

        for sym in sorted(execution_symbols):
            required = int(required_lookbacks.get(sym, 200) or 200)
            try:
                LiveMarketDataRegistry.clear_readiness(sym)
                historical = MarketDataService.ensure_historical_candles(sym, timeframe="1m", required_count=required)

                if not historical["ready"]:
                    LiveMarketDataRegistry.set_readiness(sym, required, False, historical)
                    raise RuntimeError(f"Historical data is not ready for {sym}: {historical}")

                shm, symbol_lock = self._get_shm_entry(sym)
                with symbol_lock:
                    shm = self.shm_managers.get(sym)
                if shm is None:
                    shm_size = max(10000, required + 500)
                    shm = SharedMemoryManager(sym, "1m", max_size=shm_size, create=True)
                  
                    with self._shm_registry_lock:
                        self.shm_managers[sym] = shm
                    with symbol_lock:
                        shm.preload_historical_data(required, False)
                elif shm.max_size < required:
                    raise RuntimeError(
                        f"Existing SHM capacity {shm.max_size} is below required depth {required}; controlled worker/feed restart is required to resize it"
                    )
                else:
                    with symbol_lock:
                        data = shm.get_latest_data()
                        valid_count = int(
                            ((data[:, 0] > 0)
                             & (data[:, 1] > 0)
                             & (data[:, 2] > 0)
                             & (data[:, 3] > 0)).sum()
                        )
                        if valid_count < required or historical.get("fetched", 0) > 0:
                            shm.preload_historical_data(required, False)
                LiveMarketDataRegistry.set_readiness(sym, required, True, historical)
                cache.set(LiveMarketDataRegistry.heartbeat_cache_key, time.time(), timeout=60)
                logger.info("SHM ready check for %s: required=%s capacity=%s", sym, required, shm.max_size)
            except Exception as exc:
                LiveMarketDataRegistry.set_readiness(sym, required, False, {"error": str(exc)})
                cache.set(LiveMarketDataRegistry.heartbeat_cache_key, time.time(), timeout=60)
                logger.error("Failed to prepare SHM for %s: %s", sym, exc)

        if additions:
            logger.info("Subscribed live feed to %s symbol(s) individually", len(additions))

        if removals and hasattr(self.socket, "unsubscribe"):
            for sym in sorted(removals):
                self.socket.unsubscribe(symbols=[sym], data_type="SymbolUpdate")
            logger.info("Unsubscribed live feed from %s symbol(s) individually", len(removals))

        self._subscribed_symbols = target_symbols
        return sorted(target_symbols)


    def shutdown(self):
        self._sync_stop.set()
        self._sync_wakeup.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        logger.info("Shutting down Fyers live feed threadpool...")
        try:
            if self.socket is not None:
                self.socket.close_connection()
        except Exception:
            logger.exception("Failed to close Fyers socket during shutdown")
        try:
            self.thread_pool.shutdown(wait=True, cancel_futures=True)
        except Exception:
            logger.exception("Failed to shut down feed thread pool")


    def _on_connect(self):
        logger.info("Connected to Fyers live market websocket")
        self._subscribed_symbols.clear()
        self.start_subscription_sync()
        self._sync_wakeup.set()
        try:
            self.sync_subscriptions(force=True)
        except Exception:
            logger.exception("Failed to restore Fyers subscriptions after reconnect")


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
                datetime.fromtimestamp(traded_at, tz=timezone.utc) if traded_at else datetime.now(timezone.utc)
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

            arrival_time = time.time()
            if arrival_time - self._last_health_publish.get(symbol, 0) >= 2:
                LiveMarketDataRegistry.record_tick(symbol, arrival_time)
                self._last_health_publish[symbol] = arrival_time
            cumulative_volume = float(tick.get("vol_traded_today") or 0)
            with self._volume_lock:
                previous_volume = self._last_cumulative_volume.get(symbol)
                if previous_volume is None or cumulative_volume < previous_volume:
                    # The daily cumulative total cannot be assigned to the
                    # current minute when ingestion starts mid-session.
                    volume_delta = 0.0
                else:
                    volume_delta = cumulative_volume - previous_volume
                self._last_cumulative_volume[symbol] = cumulative_volume

            # Write to ultra-fast POSIX shared memory for Execution V2
            if symbol in self.shm_managers:
                try:
                    shm, symbol_lock = self._get_shm_entry(symbol)
                    if shm is not None:
                        with symbol_lock:
                            shm.update_current_candle(
                                price=float(quote["price"]),
                                volume=volume_delta,
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
                
            except Exception as exc:
                logger.exception("Failed executing threadpool dispatch for %s: %s", symbol, exc)
