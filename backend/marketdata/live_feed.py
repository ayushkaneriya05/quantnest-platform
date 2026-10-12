import logging
import time
import threading
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
    requirements_cache_key = "marketdata:required_lookbacks"
    readiness_cache_key = f"marketdata:readiness:{settings.EXECUTION_NODE_INDEX}"
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
    def is_ready(cls, symbol, required, require_fresh=True):
        if require_fresh and not cls.is_tick_fresh(symbol):
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
        """Resolve the active universe in one instrument query per refresh."""
        from django.db.models import Q
        from paper_trading.models import PaperTradingSession
        from live_trading.models import TradingSession
        from trading.models import Order, Position

        tracked = set(cls.get_client_symbols())
        tracked.update(symbol for symbol in Position.objects.values_list("instrument__sym_ticker", flat=True) if symbol)
        tracked.update(symbol for symbol in Order.objects.filter(status="OPEN").values_list(
            "instrument__sym_ticker", flat=True) if symbol)

        requests, ids, lookbacks = [], set(), {}
        for model in (PaperTradingSession, TradingSession):
            sessions = model.objects.filter(status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"]).select_related(
                "allocation__deployed_version")
            for session in sessions:
                version = session.allocation.deployed_version if session.allocation_id else None
                config = version.config_snapshot if version else {}
                instruments = {
                    int(item["instrument_id"]) for item in config.get("watchlist_instruments", [])
                    if item.get("instrument_id") is not None
                }
                if not instruments:
                    continue
                if version.pk not in lookbacks:
                    lookbacks[version.pk] = MarketDataService.required_1m_candles(config)
                requests.append((instruments, lookbacks[version.pk]))
                ids.update(instruments)

        active = dict(Instrument.objects.filter(
            Q(pk__in=ids) | Q(sym_ticker__in=tracked), is_active=True, is_tradeable=True,
        ).values_list("pk", "sym_ticker"))
        required = {}
        for instruments, depth in requests:
            for instrument_id in instruments:
                symbol = active.get(instrument_id)
                if symbol:
                    symbol = MarketDataService.normalize_symbol(symbol)
                    required[symbol] = max(required.get(symbol, 0), depth)
        cache.set(cls.requirements_cache_key, required, timeout=cls.cache_ttl)
        return cls.set_symbols(active.values())

class MarketObservationClient:
    """Provider-neutral history, observation rings, and UI publication."""
    def __init__(self):
        self.socket = None
        self._subscribed_symbols = set()
        self._invalid_symbols = set()
        self._publication_lock = threading.Lock()
        self._publications = {}
        self._prepared_depth = {}
        self._publisher = threading.Thread(target=self._publish_quotes, name="quote-publisher", daemon=True)
        self.shm_managers = {}
        self._shm_locks = {}
        self._shm_registry_lock = threading.RLock()
        self._sync_thread = None
        self._sync_stop = threading.Event()
        self._sync_wakeup = threading.Event()
        self._volume_lock = threading.Lock()
        self._last_cumulative_volume = {}
        self._last_health_publish = {}
        self.relay = None
        self.broadcast_quotes = True
        self._publisher.start()

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
        additions = target_symbols if force else target_symbols - self._subscribed_symbols
        removals = set() if force else self._subscribed_symbols - target_symbols

        for sym in sorted(additions):
            self.socket.subscribe(symbols=[sym], data_type="SymbolUpdate")

        required_lookbacks = LiveMarketDataRegistry.get_required_lookbacks()
        from marketdata.shared_memory import SharedMemoryManager
        buffer_symbols = target_symbols
        for symbol in set(self.shm_managers) - buffer_symbols:
            shm, symbol_lock = self._get_shm_entry(symbol)
            with symbol_lock:
                if shm is not None:
                    shm.close()
                with self._shm_registry_lock:
                    self.shm_managers.pop(symbol, None)
                    self._shm_locks.pop(symbol, None)
                    self._prepared_depth.pop(symbol, None)

        for sym in sorted(buffer_symbols):
            required = int(required_lookbacks.get(sym, 2) or 2)
            if self._prepared_depth.get(sym, 0) >= required and sym in self.shm_managers:
                continue
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
                self._prepared_depth[sym] = required
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

        # Preparation belongs to the running feed, not a six-hour cache window.
        # Recreate a lost projection from buffers already prepared on this node.
        if self._prepared_depth and not cache.touch(
                LiveMarketDataRegistry.readiness_cache_key, timeout=LiveMarketDataRegistry.cache_ttl):
            for symbol, depth in self._prepared_depth.items():
                if symbol in self.shm_managers:
                    LiveMarketDataRegistry.set_readiness(symbol, depth, True, {"prepared_depth": depth})
        self._subscribed_symbols = target_symbols
        return sorted(target_symbols)

    def shutdown(self):
        self._sync_stop.set()
        self._sync_wakeup.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        logger.info("Shutting down market observation client")
        try:
            if self.socket is not None:
                self.socket.close_connection()
        except Exception:
            logger.exception("Failed to close market socket during shutdown")
        try:
            self._publisher.join(timeout=5)
            for shm in self.shm_managers.values():
                shm.close()
        except Exception:
            logger.exception("Failed to close market observation buffers")

    def ingest_observation(self, symbol, quote, volume_delta, event_time, received_time,
                           source_sequence=None, source_generation=None):
        shm, symbol_lock = self._get_shm_entry(symbol)
        if shm is not None:
            with symbol_lock:
                sequence = shm.update_current_candle(
                    price=float(quote["price"]), volume=volume_delta, timestamp=event_time,
                    received_time=received_time, source_sequence=source_sequence,
                    source_generation=source_generation)
                if not sequence:
                    return
                if self.relay is not None:
                    self.relay.emit(symbol, quote, volume_delta, event_time, received_time, sequence)
        from quantnest_runtime.signals import notify_market_change
        notify_market_change()
        if self.broadcast_quotes:
            with self._publication_lock:
                self._publications[symbol] = {**quote, "received_at": received_time}

    def _publish_quotes(self):
        # UI quotes can coalesce; observed execution ticks remain in the local ring.
        while not getattr(self, "_sync_stop", threading.Event()).is_set():
            with self._publication_lock:
                quotes, self._publications = self._publications, {}
            for symbol, quote in quotes.items():
                try:
                    MarketDataStreamer.publish_tick(symbol, quote)
                    if time.time() - self._last_health_publish.get(symbol, 0) >= 2:
                        LiveMarketDataRegistry.record_tick(symbol, quote.get("received_at"))
                        self._last_health_publish[symbol] = time.time()
                except Exception:
                    logger.exception("Quote publication failed symbol=%s", symbol)
            time.sleep(0.05)


class FyersLiveFeedClient(MarketObservationClient):
    """Fyers transport and normalization; shared consumers receive canonical observations."""

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

    def _on_connect(self):
        logger.info("Connected to Fyers live market websocket")
        self._subscribed_symbols.clear()
        self._prepared_depth.clear()
        self.start_subscription_sync()
        self._sync_wakeup.set()

    def _on_close(cls, ws=None, code=None, reason=None):
        logger.info("Market WebSocket connection closed. Code=%s", code)
        for market in tuple(cls.shm_managers.values()):
            market.mark_gap()
        if cls.relay:
            cls.relay.rotate()
        if cls.socket and getattr(cls.socket, "reconnect", False):
            pass
        # Notify users with active live sessions about feed disconnection
        from django.core.cache import cache
        throttle_key = "market_feed_disconnect_notification"
        if not cache.get(throttle_key):
            try:
                from live_trading.models import TradingSession
                from notifications.services import NotificationService
                from common.enums import NotificationType
                notified_users = set()
                for session in TradingSession.objects.filter(status="RUNNING").select_related("user"):
                    if session.user_id not in notified_users:
                        NotificationService.notify(
                            user=session.user,
                            title="Live market data feed disconnected",
                            message="Live strategies are not receiving fresh quotes. The feed will need to reconnect before entries can resume.",
                            type=NotificationType.CRITICAL,
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

            self.ingest_observation(symbol, quote, volume_delta, traded_at_dt.timestamp(), time.time())
