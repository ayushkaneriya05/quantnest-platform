import logging
from datetime import timedelta

from celery import shared_task

from django.core.cache import cache
from django.utils import timezone

from .live_feed import LiveMarketDataRegistry
from .services import FyersHistoricalDataService, MarketDataService

logger = logging.getLogger(__name__)


@shared_task(name="marketdata.refresh_live_market_subscriptions")
def refresh_live_market_subscriptions():
    symbols = LiveMarketDataRegistry.refresh_from_active_accounts()
    return {"symbols": symbols, "count": len(symbols)}


@shared_task(name="marketdata.process_market_event", queue="tick")
def process_market_event(symbol, quote, candle_state=None):
    """
    Fan out a normalized market event to downstream engines away from the
    provider websocket callback thread.
    """
    processed = {"paper": False, "terminal": False, "live": False}

    try:
        from paper_trading.tasks import process_paper_tick

        process_paper_tick.delay(symbol, quote=quote, quote_already_cached=True)
        processed["paper"] = True
    except Exception:
        logger.exception("Failed dispatching market event to paper engine for %s", symbol)
        processed["paper"] = False

    try:
        from trading.tasks import process_terminal_tick

        process_terminal_tick.delay(symbol, quote)
        processed["terminal"] = True
    except Exception:
        logger.exception("Failed dispatching market event to trading terminal for %s", symbol)
        processed["terminal"] = False

    try:
        from live_trading.tasks import process_live_tick

        process_live_tick.delay(symbol, quote=quote, quote_already_cached=True, candle_state=candle_state)
        processed["live"] = True
    except Exception:
        logger.exception("Failed dispatching market event to live engine for %s", symbol)
        processed["live"] = False

    return processed


@shared_task(name="marketdata.backfill_missing_candles")
def backfill_missing_candles(symbol, lookback_days=10, timeframe="1m", **_ignored):
    normalized_symbol = MarketDataService.normalize_symbol(symbol)
    lock_key = f"marketdata:backfill:{normalized_symbol}:{timeframe}"
    if cache.get(lock_key):
        return {"queued": False, "reason": "already_recently_requested"}

    cache.set(lock_key, True, timeout=60 * 5)
    end_dt = timezone.now()
    start_dt = end_dt - timedelta(days=int(lookback_days or 10))
    chunk_days = 90
    fetched_count = 0
    chunk_start = start_dt.date()
    end_date = end_dt.date()

    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end_date)
        fetched = FyersHistoricalDataService.fetch_and_store(
            symbol=normalized_symbol,
            date_from=chunk_start.isoformat(),
            date_to=chunk_end.isoformat(),
            timeframe=timeframe,
        )
        fetched_count += len(fetched or [])
        chunk_start = chunk_end + timedelta(days=1)

    return {
        "queued": True,
        "symbol": normalized_symbol,
        "resolution": timeframe,
        "fetched": fetched_count,
    }


@shared_task(name="marketdata.fetch_live_candles_from_broker")
def fetch_live_candles_from_broker():
    """
    Periodically fetches the official 1m candles from the broker for all actively tracked symbols.
    This replaces the local tick-based candle aggregator with perfectly accurate historical data.
    """
    from .streaming import MarketDataStreamer
    from .candle_engine import LiveCandleStore
    
    symbols = LiveMarketDataRegistry.get_symbols()
    if not symbols:
        return {"fetched_symbols": 0}
        
    end_dt = timezone.now()
    start_dt = end_dt - timedelta(minutes=5)
    
    fetched_count = 0
    for symbol in symbols:
        try:
            fetched = FyersHistoricalDataService.fetch_and_store(
                symbol=symbol,
                date_from=start_dt.isoformat(),
                date_to=end_dt.isoformat(),
                timeframe="1m"
            )
            if fetched:
                from types import SimpleNamespace
                # The latest fetched candle is the most recently closed (or still forming) candle
                # Publish it to frontend as candle.closed to overwrite any tick-built inaccuracies
                latest_candle = fetched[-1]
                candle_obj = SimpleNamespace(**latest_candle)
                MarketDataStreamer.publish_candle_update(symbol, candle_obj, event_type="candle.closed")
                
                # Update Redis buffer
                serialized = {
                    "time": int(latest_candle["time"].timestamp()),
                    "open": float(latest_candle["open"]),
                    "high": float(latest_candle["high"]),
                    "low": float(latest_candle["low"]),
                    "close": float(latest_candle["close"]),
                    "volume": int(latest_candle["volume"]),
                }
                LiveCandleStore.update_buffer(symbol, "1m", serialized)
                
                fetched_count += 1
        except Exception as exc:
            logger.exception("Failed fetching live candles from broker for %s: %s", symbol, exc)
            
    return {"fetched_symbols": fetched_count}


@shared_task(name="marketdata.reconcile_daily_market_data")
def reconcile_daily_market_data():
    """
    Runs daily at 23:55 to check if the market was officially open today.
    If the benchmark index returns no data for the 1D timeframe, it means it was a mock session or holiday.
    We then safely wipe all fake candles recorded today across ALL symbols.
    """
    from .services import FyersHistoricalDataService
    from .models import Candle
    
    end_dt = timezone.now()
    start_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    benchmark_symbol = "NSE:NIFTY50-INDEX"
    
    try:
        # Check if the benchmark index has a 1D candle for today
        fetched = FyersHistoricalDataService.fetch_and_store(
            symbol=benchmark_symbol,
            date_from=start_dt.isoformat(),
            date_to=end_dt.isoformat(),
            timeframe="1D"
        )
        
        # If Fyers returns nothing (or it was an empty day), it's a mock session / holiday
        if not fetched:
            logger.info("Daily reconciliation: No valid data found for benchmark index. Wiping today's mock/holiday candles.")
            
            # Delete all candles recorded today for ALL symbols
            deleted, _ = Candle.objects.filter(time__gte=start_dt, time__lt=end_dt).delete()
            logger.info(f"Deleted {deleted} fake mock candles from database.")
            
            # Flush Redis candle cache
            keys = cache.keys("marketdata:candles:*")
            if keys:
                cache.delete_many(keys)
                logger.info(f"Flushed {len(keys)} Redis candle cache keys.")
                
            return {"status": "wiped_mock_data", "deleted": deleted}
            
        else:
            logger.info("Daily reconciliation: Benchmark index traded today. Keeping all recorded candles.")
            return {"status": "official_session_kept", "deleted": 0}
            
    except Exception as exc:
        logger.exception("Failed running daily reconciliation task: %s", exc)
        return {"status": "error", "error": str(exc)}
