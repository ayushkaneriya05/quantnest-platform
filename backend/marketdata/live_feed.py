"""Shared live demand, confirmed subscriptions and local observation preparation."""
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from common.redis import runtime_redis
from instruments.models import Instrument
from .contracts import HistoryRequest, OHLCV, normalize_symbol
from .streaming import MarketDataStreamer

logger = logging.getLogger(__name__)


class LiveMarketDataRegistry:
    client_key = "marketdata:client_subscriptions"
    state_ttl = 30

    @staticmethod
    def key(suffix):
        return f"quantnest:marketdata:{settings.MARKET_DATA_PROVIDER}:{suffix}"

    @classmethod
    def request_refresh(cls):
        runtime_redis().incr(cls.key("demand_revision"))

    @classmethod
    def refresh_client_subscriptions(cls, symbols, connection):
        if symbols:
            runtime_redis().zadd(cls.client_key, {
                json.dumps([normalize_symbol(symbol), connection]): time.time() for symbol in symbols})

    @classmethod
    def remove_client_subscription(cls, symbol, connection):
        runtime_redis().zrem(cls.client_key, json.dumps([normalize_symbol(symbol), connection]))

    @classmethod
    def get_state(cls):
        value = runtime_redis().get(cls.key("state"))
        state = json.loads(value) if value else {}
        if not 0 <= time.time() - state.get("updated_at", 0) < cls.state_ttl:
            return {}
        state["subscribed"] = set(state["subscribed"])
        return state

    @staticmethod
    def is_ready(symbol, required, state):
        prepared = state.get("prepared", {}).get(symbol, {})
        return (state.get("connected", False) and symbol in state.get("subscribed", ()) and prepared.get("ready", False)
                and all(prepared.get("depths", {}).get(source, 0) >= depth for source, depth in required.items()))

    @classmethod
    def resolve_demand(cls, subscribed, invalid):
        """Resolve one feed snapshot. {} means ticks only."""
        from execution.demand import market_requirements
        from .providers import provider

        client = runtime_redis()
        client.zremrangebyscore(cls.client_key, "-inf", time.time() - 75)
        browser = {json.loads(value)[0] for value in client.zrange(cls.client_key, 0, -1)}
        execution, exposure = market_requirements()
        available = set(Instrument.objects.filter(sym_ticker__in=browser, is_active=True).values_list("sym_ticker", flat=True))
        ordered = sorted((execution.keys() | available) - invalid, key=lambda symbol: (
            0 if symbol in exposure else 1 if symbol in execution else 2,
            symbol not in subscribed, symbol))
        capacity = provider().subscription_limit
        requirements = {symbol: execution.get(symbol, {}) for symbol in ordered[:capacity]}
        rejected = {symbol: "Market-data subscription capacity is full." for symbol in ordered[capacity:]}
        rejected.update({symbol: "This instrument is unavailable for market data."
                         for symbol in browser - available - invalid})
        return requirements, rejected, browser



class MarketObservationClient:
    """Provider callbacks write ticks; background loops manage all control I/O."""
    subscription_batch_size = 500

    def __init__(self):
        self.socket = None
        self._connected = threading.Event()
        self._connected_at = 0.0
        self._generation = uuid.uuid4().hex
        self._subscribed_symbols, self._invalid_symbols = set(), set()
        self._pending = None
        self._retry_at, self._next_demand, self._demand_revision = 0, 0, None
        self._subscription_error = ""
        self._disconnect_notice = threading.Event()
        self._targets, self._rejected, self._prepared, self._markers = {}, {}, {}, {}
        self._browser_symbols = set()
        self._retry_history, self._calendars = {}, {}
        self._state_lock = threading.RLock()
        self._publication_lock, self._publications = threading.Lock(), {}
        self.shm_managers, self.daily_managers, self._shm_locks = {}, {}, {}
        self._sync_thread = self._history_thread = None
        self._sync_stop, self._sync_wakeup, self._history_wakeup = threading.Event(), threading.Event(), threading.Event()
        from .charts import LiveChartPublisher
        self._chart_publisher = LiveChartPublisher()
        self._publisher = threading.Thread(target=self._publish_quotes, name="quote-publisher", daemon=True)
        self._publisher.start()

    def connect(self):
        raise NotImplementedError

    def subscribe_symbols(self, symbols: list[str]) -> None:
        raise NotImplementedError

    def unsubscribe_symbols(self, symbols: list[str]) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def mark_connected(self):
        # The SDK can reconnect internally without invoking its close callback.
        if self._connected.is_set():
            self.mark_disconnected()
        with self._state_lock:
            self._generation = uuid.uuid4().hex
            self._subscribed_symbols.clear()
            self._invalid_symbols.clear()
            self._retry_at = 0
            self._pending = None
            self._prepared.clear()
            self._markers.clear()
            self._next_demand = 0
            self._connected_at = time.time()
            self._connected.set()
        self._sync_wakeup.set()

    def mark_disconnected(self):
        with self._state_lock:
            if not self._connected.is_set():
                return  # SDK error and close callbacks can describe the same outage.
            self._disconnect_notice.set()
            self._connected.clear()
            self._pending = None
            self._prepared.clear()
            self._markers.clear()
            self._subscribed_symbols.clear()
        for symbol, market in tuple(self.shm_managers.items()):
            with self._symbol_lock(symbol):
                if self.shm_managers.get(symbol) is market:
                    market.mark_gap()

    def subscription_result(self, operation, successful, error=""):
        """One outstanding batch makes SDK acknowledgements unambiguous."""
        with self._state_lock:
            if self._pending is None or self._pending[0] != operation:
                return
            _, symbols, _ = self._pending
            if successful:
                if operation == "subscribe":
                    self._subscribed_symbols.update(set(symbols) - self._invalid_symbols)
                else:
                    self._subscribed_symbols.difference_update(symbols)
                self._subscription_error = ""
            else:
                self._retry_at = time.monotonic() + 5
                self._subscription_error = error or "Provider subscription request failed."
                logger.warning("%s", self._subscription_error)
            self._pending = None
        self._sync_wakeup.set()
        self._history_wakeup.set()

    def _notify_disconnect(self):
        if not self._disconnect_notice.is_set():
            return
        self._disconnect_notice.clear()
        if not cache.add("market_feed_disconnect_notification", True, 600):
            return
        from live_trading.models import TradingSession
        from notifications.services import NotificationService
        from common.enums import NotificationType
        for user_id in TradingSession.objects.filter(status="RUNNING").values_list("user_id", flat=True).distinct():
            NotificationService.notify(user_id=user_id, title="Live market data feed disconnected",
                message="Live strategies need the feed to reconnect and publish observations before new entries can resume.",
                type=NotificationType.CRITICAL, data={"module": "marketdata"})

    def _publish_state(self):
        with self._state_lock:
            state = {
                "generation": self._generation,
                "connected": self._connected.is_set(), "updated_at": time.time(),
                "requirements": self._targets, "rejected": {**self._rejected, **{
                    symbol: "The provider rejected this instrument symbol." for symbol in self._invalid_symbols}},
                "subscribed": sorted(self._subscribed_symbols), "prepared": self._prepared,
                "subscription_error": self._subscription_error,
            }
            value = json.dumps(state)
        runtime_redis().set(LiveMarketDataRegistry.key("state"),
                            value, ex=LiveMarketDataRegistry.state_ttl)

    def start_subscription_sync(self):
        if self._sync_thread and self._sync_thread.is_alive():
            return
        def subscriptions():
            from django.db import close_old_connections
            while not self._sync_stop.is_set():
                try:
                    close_old_connections()
                    self.sync_subscriptions()
                    self._publish_state()
                    self._notify_disconnect()
                except Exception:
                    logger.exception("Market subscription reconciliation failed")
                finally:
                    close_old_connections()
                self._sync_wakeup.wait(1)
                self._sync_wakeup.clear()
        def history():
            from django.db import close_old_connections
            while not self._sync_stop.is_set():
                try:
                    close_old_connections()
                    self.prepare_history()
                except Exception:
                    logger.exception("Market history preparation failed")
                finally:
                    close_old_connections()
                self._history_wakeup.wait(5)
                self._history_wakeup.clear()
        self._sync_thread = threading.Thread(target=subscriptions, name="market-subscriptions", daemon=True)
        self._history_thread = threading.Thread(target=history, name="market-history", daemon=True)
        self._sync_thread.start()
        self._history_thread.start()

    def _symbol_lock(self, symbol):
        with self._state_lock:
            return self._shm_locks.setdefault(symbol, threading.RLock())

    def sync_subscriptions(self):
        from .shared_memory import SharedMemoryManager
        if not self._connected.is_set():
            return
        revision = runtime_redis().get(LiveMarketDataRegistry.key("demand_revision"))
        if time.monotonic() >= self._next_demand or revision != self._demand_revision:
            self._targets, self._rejected, self._browser_symbols = LiveMarketDataRegistry.resolve_demand(
                self._subscribed_symbols, self._invalid_symbols)
            self._demand_revision, self._next_demand = revision, time.monotonic() + 15
        targets = {symbol: depths for symbol, depths in self._targets.items() if symbol not in self._invalid_symbols}
        for symbol, depths in targets.items():
            with self._symbol_lock(symbol):
                if not depths:
                    old_daily = self.daily_managers.pop(symbol, None)
                    if old_daily:
                        old_daily.close()
                    with self._state_lock:
                        for values in (self._prepared, self._markers, self._retry_history, self._calendars):
                            values.pop(symbol, None)
                if symbol not in self.shm_managers:
                    market = SharedMemoryManager(
                        symbol, "1m", max_size=max(10000, depths.get("1m", 0) + 500), create=True)
                    if market.tick_counter:
                        market.mark_gap()  # Reusing an old writer's buffer requires a new quote.
                    self.shm_managers[symbol] = market
        with self._state_lock:
            self._targets = targets
        for symbol in set(self.shm_managers) - targets.keys():
            with self._symbol_lock(symbol):
                self.shm_managers.pop(symbol).close()
                daily = self.daily_managers.pop(symbol, None)
                if daily:
                    daily.close()
                with self._state_lock:
                    for values in (self._prepared, self._markers, self._retry_history, self._calendars):
                        values.pop(symbol, None)
        with self._state_lock:
            pending = self._pending
        if pending and time.monotonic() >= pending[2]:
            # Reconnect before another batch: late SDK acknowledgements have no IDs.
            self._subscription_error = "Subscription acknowledgement timed out; reconnecting."
            logger.warning("%s operation=%s symbols=%s", self._subscription_error, pending[0], len(pending[1]))
            self.mark_disconnected()
            self.disconnect()
            self.connect()
            return
        with self._state_lock:
            if self._pending or time.monotonic() < self._retry_at:
                return
            removals = sorted(self._subscribed_symbols - targets.keys())
            additions = [symbol for symbol in targets if symbol not in self._subscribed_symbols]
            operation, symbols = ("unsubscribe", removals) if removals else ("subscribe", additions)
            symbols = symbols[:self.subscription_batch_size]
            if not symbols:
                return
            self._pending = operation, symbols, time.monotonic() + 20
        try:
            if operation == "subscribe":
                self.subscribe_symbols(symbols)
            else:
                self.unsubscribe_symbols(symbols)
        except Exception as exc:
            self.subscription_result(operation, False, str(exc))
        self._history_wakeup.set()

    def prepare_history(self):
        import numpy as np
        from .calendar import MarketSessionCalendar
        from .candles import read_source
        from .history import ensure_history, revision_key
        from .shared_memory import SharedMemoryManager
        if not self._connected.is_set():
            return
        with self._state_lock:
            targets = {symbol: dict(depths) for symbol, depths in self._targets.items()
                       if depths and symbol in self._subscribed_symbols}
            generation = self._generation
            connected_at = self._connected_at
        revisions = dict(zip(targets, runtime_redis().mget([revision_key(symbol) for symbol in targets]))) if targets else {}
        for symbol, required in targets.items():
            if self._sync_stop.is_set():
                return
            with self._state_lock:
                if not self._connected.is_set() or self._generation != generation:
                    return  # Do not fetch the rest of a disconnected generation.
            if time.monotonic() < self._retry_history.get(symbol, 0):
                continue
            acquire, retry_delay = True, 30
            try:
                now = datetime.now(timezone.utc)
                cached = self._calendars.get(symbol)
                if cached is None or time.monotonic() - cached[0] >= 60:
                    instrument = Instrument.objects.get(sym_ticker=symbol)
                    calendar = MarketSessionCalendar.for_instrument(instrument)
                    start = min(calendar.warmup_start(now, depth, source=source) for source, depth in required.items())
                    calendar.load_holidays(start.date() - timedelta(days=7), now.astimezone(calendar.zone).date() + timedelta(days=31))
                    self._calendars[symbol] = time.monotonic(), instrument, calendar
                else:
                    _, instrument, calendar = cached
                market = self.shm_managers.get(symbol)
                if market is None:
                    continue
                gap = market.source_gap
                if gap and "1m" in required:
                    reconnected = datetime.fromtimestamp(connected_at, timezone.utc)
                    recovery_end = reconnected.replace(second=0, microsecond=0) + timedelta(minutes=1)
                    if calendar.is_open(reconnected) and now < recovery_end:
                        continue  # Fetch the interrupted minute only after it has completed.
                daily = calendar.completed_horizon("1D", now) if "1D" in required else 0
                marker = (int(revisions[symbol] or 0), calendar.signature, daily, gap, tuple(sorted(required.items())))
                previous = self._markers.get(symbol)
                if marker == previous:
                    continue
                acquire = previous is None or marker[1:] != previous[1:]
                prepared, through = {}, {}
                for source, depth in required.items():
                    with self._state_lock:
                        if not self._connected.is_set() or self._generation != generation:
                            return
                    start = calendar.warmup_start(now, depth, source=source)
                    request = HistoryRequest(instrument, source, start, now, calendar)
                    if acquire:
                        result = ensure_history(request, max_requests=1)
                        with self._state_lock:
                            if not self._connected.is_set() or self._generation != generation:
                                return
                        if not result.complete:
                            retry_delay = 30 if result.error else 5
                            raise ValueError(result.error or "Required history is still being prepared.")

                    batch = read_source(request)
                    if batch.frame.empty:
                        raise ValueError(f"No completed {source} observations are available.")
                    if len(batch.frame) < depth:
                        raise ValueError(f"Insufficient completed {source} history: {len(batch.frame)} available; {depth} required.")
                    if acquire and not batch.quality["complete"]:
                        raise ValueError("Required history acquisition is incomplete.")
                    frame = batch.frame.tail(depth)
                    through[source] = frame.index[-1].timestamp()
                    prepared[source] = np.column_stack((
                        frame.loc[:, list(OHLCV)].to_numpy(dtype=float), frame.index.as_unit("s").asi8))
                with self._symbol_lock(symbol):
                    with self._state_lock:
                        if self._sync_stop.is_set() or self._generation != generation or self._targets.get(symbol) != required:
                            continue
                    for source, rows in prepared.items():
                        managers = self.shm_managers if source == "1m" else self.daily_managers
                        buffer = managers.get(symbol)
                        if buffer is None:
                            buffer = SharedMemoryManager(symbol, source, max_size=max(500, required[source] + 500), create=True)
                            managers[symbol] = buffer
                        if buffer.max_size < required[source]:
                            raise ValueError(f"Increase {symbol} {source} buffer capacity to {required[source]}.")
                        buffer.replace_history(rows)
                    if "1D" not in required:
                        old_daily = self.daily_managers.pop(symbol, None)
                        if old_daily:
                            old_daily.close()
                    with self._state_lock:
                        if self._generation != generation or not self._connected.is_set() or self._targets.get(symbol) != required:
                            continue
                        self._prepared[symbol] = {"ready": True, "depths": required, "prepared_through": through,
                                                  "source_gap": gap,
                                                  "updated_at": time.time(), "error": ""}
                        # Record the revision read before the data, so a concurrent
                        # correction is picked up by the next preparation pass.
                        self._markers[symbol] = marker
                        self._retry_history.pop(symbol, None)
            except Exception as exc:
                with self._state_lock:
                    if not self._connected.is_set() or self._generation != generation:
                        return
                    if symbol not in self._targets:
                        continue
                    previous = self._prepared.get(symbol, {})
                    # Existing buffers remain useful after a correction-read
                    # failure. New requirements/gaps must be prepared again.
                    ready = not acquire
                    self._prepared[symbol] = {**previous, "ready": ready and previous.get("ready", False),
                                              "error": str(exc), "updated_at": time.time()}
                    self._retry_history[symbol] = time.monotonic() + retry_delay
                logger.warning("History preparation pending symbol=%s: %s", symbol, exc)

    def shutdown(self):
        self._sync_stop.set()
        self._sync_wakeup.set()
        self._history_wakeup.set()
        self.mark_disconnected()
        self._publish_state()
        try:
            self.disconnect()
        except Exception:
            logger.exception("Could not close the market-data socket")
        for thread in (self._sync_thread, self._history_thread, self._publisher):
            if thread and thread.is_alive():
                thread.join(timeout=5)
        for symbol in tuple(self.shm_managers):
            with self._symbol_lock(symbol):
                self.shm_managers.pop(symbol).close()
                daily = self.daily_managers.pop(symbol, None)
                if daily:
                    daily.close()

    def ingest_observation(self, symbol, quote, volume_delta, event_time, received_time):
        if self._sync_stop.is_set():
            return
        with self._symbol_lock(symbol):
            if not self._connected.is_set():
                return  # Ignore queued messages from the disconnected transport.
            market = self.shm_managers.get(symbol)
            if market is None:
                return
            sequence = market.update_current_candle(
                price=float(quote["price"]), volume=volume_delta, timestamp=event_time,
                received_time=received_time)
            if not sequence:
                return
        with self._publication_lock:
            self._publications[symbol] = quote

    def read_observations(self, symbol, lookback):
        import numpy as np
        with self._symbol_lock(symbol):
            market = self.shm_managers.get(symbol)
            return market.get_latest_data(lookback or None) if market else np.empty((0, 6))

    def _publish_quotes(self):
        from .quotes import publish_quote
        while not self._sync_stop.is_set():
            with self._publication_lock:
                quotes, self._publications = self._publications, {}
            for symbol, quote in quotes.items():
                try:
                    payload = publish_quote(symbol, quote)
                    # Valuations retain the latest quote even with no browser open.
                    # Execution-only symbols need no Channels fanout or chart work.
                    if symbol in self._browser_symbols:
                        MarketDataStreamer.publish(MarketDataStreamer.symbol_group(symbol), {"type": "tick", "data": payload})
                        self._chart_publisher.publish(symbol, self.read_observations)
                except Exception:
                    logger.exception("Quote publication failed symbol=%s", symbol)
            self._sync_stop.wait(0.05)
