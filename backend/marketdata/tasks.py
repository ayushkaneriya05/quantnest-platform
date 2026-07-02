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

        process_paper_tick.delay(symbol, quote=quote, quote_already_cached=True, candle_state=candle_state)
        processed["paper"] = True
    except Exception:
        logger.exception("Failed dispatching market event to paper engine for %s", symbol)
        processed["paper"] = False

    try:
        from trading.tasks import process_terminal_tick

        process_terminal_tick.delay(symbol, quote, candle_state=candle_state)
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
