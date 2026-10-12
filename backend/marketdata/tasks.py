import logging
from datetime import timedelta

from celery import shared_task

from django.core.cache import cache
from django.utils import timezone

from .live_feed import LiveMarketDataRegistry
from .services import MarketDataService

logger = logging.getLogger(__name__)


@shared_task(name="marketdata.refresh_live_market_subscriptions")
def refresh_live_market_subscriptions():
    symbols = LiveMarketDataRegistry.refresh_from_active_accounts()
    return {"symbols": symbols, "count": len(symbols)}



@shared_task(name="marketdata.backfill_missing_candles")
def backfill_missing_candles(symbol, lookback_days=10, timeframe="1m", **_ignored):
    normalized_symbol = MarketDataService.normalize_symbol(symbol)
    lock_key = f"marketdata:backfill:{normalized_symbol}:{timeframe}"
    if not cache.add(lock_key, True, timeout=60 * 5):
        return {"queued": False, "reason": "already_recently_requested"}

    end_dt = timezone.now()
    start_dt = end_dt - timedelta(days=int(lookback_days or 10))
    chunk_days = 90
    fetched_count = 0
    chunk_start = start_dt.date()
    end_date = end_dt.date()

    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end_date)
        fetched = MarketDataService.backfill_candles_from_broker(
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

    symbols = LiveMarketDataRegistry.get_symbols()
    if not symbols:
        return {"fetched_symbols": 0}
        
    end_dt = timezone.now()
    start_dt = end_dt - timedelta(minutes=5)
    
    fetched_count = 0
    for symbol in symbols:
        try:
            fetched = MarketDataService.backfill_candles_from_broker(
                symbol=symbol,
                date_from=start_dt.isoformat(),
                date_to=end_dt.isoformat(),
                timeframe="1m"
            )
            if fetched:
                from types import SimpleNamespace
                completed = [candle for candle in fetched if candle["time"] + timedelta(minutes=1) <= end_dt]
                if not completed:
                    continue
                latest_candle = completed[-1]
                candle_obj = SimpleNamespace(**latest_candle)
                MarketDataStreamer.publish_candle_update(symbol, candle_obj, event_type="candle.closed")
                
                fetched_count += 1
        except Exception as exc:
            logger.exception("Failed fetching live candles from broker for %s: %s", symbol, exc)
            
    return {"fetched_symbols": fetched_count}


@shared_task(name="marketdata.reconcile_daily_market_data")
def reconcile_daily_market_data():
    """Repair source coverage; an empty provider response never deletes market history."""
    from marketdata.calendar import MarketSessionCalendar
    today = timezone.now()
    results = {"repaired": 0, "failed": []}
    for symbol in LiveMarketDataRegistry.get_symbols():
        calendar = MarketSessionCalendar.for_symbol(symbol)
        day = today.astimezone(calendar.zone).date()
        calendar.load_holidays(day, day)
        if not calendar.is_trading_day(day):
            continue
        try:
            candles = MarketDataService.backfill_candles_from_broker(
                symbol, day.isoformat(), day.isoformat(), "1m")
            if candles is None:
                results["failed"].append(symbol)
            else:
                results["repaired"] += 1
        except Exception:
            logger.exception("Daily data repair failed symbol=%s", symbol)
            results["failed"].append(symbol)
    return results
