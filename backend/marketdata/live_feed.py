import logging
import time
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache

from .services import TickCandleAggregator
from .streaming import MarketDataStreamer
from .utils import get_active_fyers_access_token
from .candle_engine import LiveCandleStore

try:
    from fyers_apiv3.FyersWebsocket import data_ws
except Exception:  # pragma: no cover - optional dependency at runtime
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
        normalized = sorted(
            {
                MarketDataStreamer.normalize_symbol(symbol)
                for symbol in (symbols or [])
                if symbol
            }
        )
        cache.set(cls.cache_key, normalized, timeout=cls.cache_ttl)
        return normalized

    @classmethod
    def add_symbols(cls, symbols):
        return cls.set_symbols([*cls.get_symbols(), *(symbols or [])])

    @classmethod
    def remove_symbols(cls, symbols):
        remove_set = {
            MarketDataStreamer.normalize_symbol(symbol)
            for symbol in (symbols or [])
            if symbol
        }
        return cls.set_symbols([symbol for symbol in cls.get_symbols() if symbol not in remove_set])

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
        active_symbols = set(cls.refresh_from_active_accounts())
        active_symbols.update(cls.get_client_symbols())
        return cls.set_symbols(active_symbols)

    @classmethod
    def refresh_from_active_accounts(cls):
        from paper_trading.models import PaperAccount, PaperOrder, PaperPosition
        from common.enums import StrategyStatus
        from live_trading.models import LiveOrder, LivePosition, TradingSession
        from strategies.models import Strategy
        from trading.models import Order, Position

        default_symbols = list(getattr(settings, "LIVE_MARKET_DEFAULT_SYMBOLS", []))
        tracked = set(default_symbols)
        tracked.update(cls.get_client_symbols())

        # Legacy/Strategy Paper Trading
        open_position_symbols = PaperPosition.objects.filter(
            account__is_active=True,
            account__user__isnull=False,
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in open_position_symbols if symbol)

        pending_order_symbols = PaperOrder.objects.filter(
            account__is_active=True,
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
            PaperAccount.objects.filter(is_active=True, user__isnull=False)
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
                capital_allocation__is_active=True,
            )
            .prefetch_related("watchlist_instruments__instrument")
            .distinct()
        )
        for strategy in paper_strategies:
            for watch in strategy.watchlist_instruments.all():
                if watch.instrument and watch.instrument.sym_ticker:
                    tracked.add(watch.instrument.sym_ticker)

        live_position_symbols = LivePosition.objects.filter(
            user__isnull=False,
        ).values_list("instrument__sym_ticker", flat=True)
        tracked.update(symbol for symbol in live_position_symbols if symbol)

        # ... (rest of live trading symbols) ...
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
            .prefetch_related("strategy__watchlist_instruments__instrument")
            .distinct()
        )
        for session in live_sessions:
            for watch in session.strategy.watchlist_instruments.all():
                if watch.instrument and watch.instrument.sym_ticker:
                    tracked.add(watch.instrument.sym_ticker)

        return cls.set_symbols(tracked)


class FyersLiveFeedClient:
    def __init__(self):
        self.socket = None
        self._subscribed_symbols = set()
        self._invalid_symbols = set()

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
            logger.info("Subscribed live feed to %s symbol(s) individually", len(additions))

        if removals and hasattr(self.socket, "unsubscribe"):
            for sym in sorted(removals):
                self.socket.unsubscribe(symbols=[sym], data_type="SymbolUpdate")
            logger.info("Unsubscribed live feed from %s symbol(s) individually", len(removals))

        self._subscribed_symbols = target_symbols
        return sorted(target_symbols)

    def run_forever(self, poll_interval=15):
        if self.socket is None:
            self.connect()

        while True:
            try:
                self.sync_subscriptions()
            except Exception as exc:  # pragma: no cover - long-running process safety
                logger.exception("Failed syncing live subscriptions: %s", exc)
            time.sleep(poll_interval)

    def _on_connect(self):
        logger.info("Connected to Fyers live market websocket")
        self.sync_subscriptions(force=True)

    def _on_close(self, message):
        logger.warning("Fyers live websocket closed: %s", message)

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

    def _on_message(self, tick):
        if not isinstance(tick, dict):
            return

        symbol = tick.get("symbol")
        if not symbol:
            return
        ltp = tick.get("ltp")
        if ltp in (None, "", 0, "0"):
            logger.debug("Skipping market tick without a valid price for %s", symbol)
            return

        traded_at = tick.get("last_traded_time")
        traded_at_dt = (
            datetime.fromtimestamp(traded_at, tz=timezone.utc)
            if traded_at
            else datetime.now(timezone.utc)
        )

        quote = {
            "price": ltp,
            "open": tick.get("open_price"),
            "high": tick.get("high_price"),
            "low": tick.get("low_price"),
            "close": tick.get("prev_close_price"),
            "change": tick.get("ch"),
            "change_percent": tick.get("chp"),
            "volume": tick.get("vol_traded_today"),
            "last_traded_qty": tick.get("last_traded_qty"),
            "avg_trade_price": tick.get("avg_trade_price"),
            "timestamp": traded_at_dt.isoformat(),
        }
        MarketDataStreamer.update_quote(symbol, quote)
        finalized_candle, active_candle = TickCandleAggregator.process_tick(symbol, quote)
        serialized_active = None
        if active_candle:
            from marketdata.services import MarketDataService
            serialized_active = MarketDataService.serialize_candle_state(active_candle)
            LiveCandleStore.update_buffer(symbol, "1m", serialized_active)
            
            # Real-time 1D candle update using broker's native Daily OHLCV from the tick
            daily_time = MarketDataService.align_time(traded_at_dt, "day", 1)
            serialized_daily = {
                "time": int(daily_time.timestamp()),
                "open": float(quote["open"] if quote["open"] else quote["price"]),
                "high": float(quote["high"] if quote["high"] else quote["price"]),
                "low": float(quote["low"] if quote["low"] else quote["price"]),
                "close": float(quote["price"]),
                "volume": int(quote["volume"] or 0),
            }
            LiveCandleStore.update_buffer(symbol, "1D", serialized_daily)
            
            MarketDataStreamer.publish_candle_update(symbol, active_candle)
        if finalized_candle:
            MarketDataStreamer.publish_candle_update(symbol, finalized_candle, event_type="candle.closed")

        try:
            from .tasks import process_market_event

            process_market_event.delay(symbol, quote, candle_state=serialized_active)
        except Exception as exc:
            logger.exception("Failed dispatching downstream market event for %s: %s", symbol, exc)
