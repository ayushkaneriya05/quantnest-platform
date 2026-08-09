import logging
import time
import concurrent.futures
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache

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
        
        # We NO LONGER call refresh_from_active_accounts() here because it causes
        # severe ASGI threadpool exhaustion and SQLite deadlocks during rapid 
        # WebSocket reconnects (e.g., page reloads, HMR).
        # The Celery beat task 'refresh_live_market_subscriptions' will handle
        # syncing the master subscription list every 30 seconds.
        return cls.get_symbols()

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

        if not tracked:
            return cls.set_symbols([])

        from instruments.models import Instrument
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
        
        # Start L1 Cache background sync when socket connects
        from marketdata.l1_cache import tick_cache
        tick_cache.start_background_sync(interval_seconds=3)
        
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

        try:
            while True:
                try:
                    self.sync_subscriptions()
                except Exception as exc:  # pragma: no cover - long-running process safety
                    logger.exception("Failed syncing live subscriptions: %s", exc)
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        logger.info("Shutting down Fyers live feed threadpool...")
        self.thread_pool.shutdown(wait=True)

    def _on_connect(self):
        logger.info("Connected to Fyers live market websocket")
        self.sync_subscriptions(force=True)

    def _on_close(cls, ws=None, code=None, reason=None):
        logger.info(f"Fyers WebSocket connection closed. Code: {code}, Reason: {reason}")
        from marketdata.l1_cache import tick_cache
        tick_cache.stop_background_sync()
        if cls.socket and getattr(cls.socket, "reconnect", False):
            pass

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
            # Real-time 1D candle update using broker's native Daily OHLCV from the tick
            from marketdata.services import MarketDataService
            daily_time = MarketDataService.align_time(traded_at_dt, "day", 1)
            serialized_daily = {
                "time": int(daily_time.timestamp()),
                "open": float(quote["day_open"] if quote["day_open"] else quote["price"]),
                "high": float(quote["day_high"] if quote["day_high"] else quote["price"]),
                "low": float(quote["day_low"] if quote["day_low"] else quote["price"]),
                "close": float(quote["price"]),
                "volume": int(quote["volume"] or 0),
            }
            
            minute_time = MarketDataService.align_time(traded_at_dt, "minute", 1)
            serialized_1m = {
                "time": int(minute_time.timestamp()),
                "open": float(quote["price"]),
                "high": float(quote["price"]),
                "low": float(quote["price"]),
                "close": float(quote["price"]),
                "volume": 0,
            }
            
            candle_states = {
                "1D": serialized_daily,
                "1m": serialized_1m,
            }
            # Throttle Redis/DB updates to max 1 per second per symbol
            now = time.time()
            if now - self.last_candle_updates.get(symbol, 0) >= 1.0:
                self.last_candle_updates[symbol] = now
                try:
                    LiveCandleStore.update_buffer(symbol, "1D", serialized_daily)
                except Exception as exc:
                    logger.exception("Failed updating live candle buffer for %s: %s", symbol, exc)

            def _dispatch_terminal():
                try:
                    from trading.services import TradingOrderService
                    from marketdata.l1_cache import tick_cache
                    open_orders = tick_cache.get_terminal_orders(symbol)
                    if open_orders:
                        TradingOrderService.process_matching_engine(symbol, quote, open_orders=open_orders)
                except Exception as exc:
                    logger.exception("Terminal matching error for %s: %s", symbol, exc)
                    
            def _dispatch_paper():
                try:
                    from paper_trading.services import PaperStrategyEngine, PaperExecutionService
                    from marketdata.l1_cache import tick_cache
                    
                    # 1. First process any pending Limit/Stop orders for Paper strategies
                    def _paper_matching_task():
                        try:
                            PaperExecutionService.process_pending_strategy_orders(symbol, quote, quote_already_cached=True)
                        except Exception as e:
                            logger.error("Paper matching engine error: %s", e)
                    self.thread_pool.submit(_paper_matching_task)

                    # 2. Then evaluate new strategy signals
                    strategies = tick_cache.get_paper_strategies(symbol)
                    for strat_data in strategies:
                        def _paper_task(strat_item):
                            try:
                                PaperStrategyEngine.process_tick(
                                    strat_item["strategy"], 
                                    session=strat_item.get("session"), 
                                    symbol=symbol, 
                                    candle_states=candle_states
                                )
                            except Exception as e:
                                logger.error("Paper strategy %s error: %s", strat_item["strategy"].id, e)
                        self.thread_pool.submit(_paper_task, strat_data)
                except Exception as exc:
                    logger.exception("Paper fanning error for %s: %s", symbol, exc)

            def _dispatch_live():
                try:
                    from live_trading.services import LiveExecutionService
                    from marketdata.l1_cache import tick_cache
                    sessions = tick_cache.get_live_sessions(symbol)
                    for session in sessions:
                        def _live_task(sess):
                            try:
                                LiveExecutionService.execute_session_once(sess, symbol, candle_states=candle_states)
                            except Exception as e:
                                logger.error("Live session %s error: %s", sess.id, e)
                        self.thread_pool.submit(_live_task, session)
                except Exception as exc:
                    logger.exception("Live fanning error for %s: %s", symbol, exc)

            try:
                from marketdata.l1_cache import tick_cache
                # Ensure TickCache is synced
                if tick_cache.last_sync is None:
                    tick_cache.force_sync()
                    
                # Broadcast to frontend websockets via Django Channels
                MarketDataStreamer.update_quote(symbol, quote)
                
                # Instantly dispatch the engine fan-outs to the ThreadPool
                self.thread_pool.submit(_dispatch_terminal)
                self.thread_pool.submit(_dispatch_paper)
                self.thread_pool.submit(_dispatch_live)
            except Exception as exc:
                logger.exception("Failed executing threadpool dispatch for %s: %s", symbol, exc)
