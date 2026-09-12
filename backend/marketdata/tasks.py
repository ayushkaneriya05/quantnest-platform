"""
marketdata/tasks.py — Celery tasks for market-data maintenance.

Key fixes:
  * ``reconcile_daily_market_data`` no longer mass-deletes candles when the
    broker returns an empty response.  Canonical data is never deleted merely
    because an API call returned no data.
  * ``fetch_live_candles_from_broker`` uses per-symbol locks to prevent
    overlapping reconciliation runs.
  * ``backfill_missing_candles`` uses the central MarketDataRepository for
    exact coverage detection rather than simple date-range downloads.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from .live_feed import LiveMarketDataRegistry
from .services import MarketDataService
from .trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)

# Per-symbol lock TTL for live minute reconciliation (seconds)
_RECONCILE_LOCK_TTL = 90


@shared_task(name="marketdata.refresh_live_market_subscriptions")
def refresh_live_market_subscriptions():
    symbols = LiveMarketDataRegistry.refresh_from_active_accounts()
    return {"symbols": symbols, "count": len(symbols)}


@shared_task(name="marketdata.backfill_missing_candles")
def backfill_missing_candles(symbol, lookback_days=10, timeframe="1m", **_ignored):
    """
    Backfill any missing canonical candles for *symbol* over the last
    *lookback_days*.  Uses exact coverage detection via MarketDataRepository
    so that only genuinely missing ranges are downloaded from FYERS.
    """
    from .market_data_repository import (
        BrokerError,
        DataIncompleteError,
        get_repository,
    )

    normalized_symbol = MarketDataService.normalize_symbol(symbol)
    tf = MarketDataService.normalize_timeframe(timeframe)

    # Canonical backing check (backfill only stores canonical data)
    from .models import CANONICAL_TIMEFRAMES
    if tf not in CANONICAL_TIMEFRAMES:
        logger.warning(
            "backfill_missing_candles: %r is not a canonical timeframe; skipping.", tf
        )
        return {"queued": False, "reason": "non_canonical_timeframe"}

    lock_key = f"marketdata:backfill:{normalized_symbol}:{tf}"
    if not cache.add(lock_key, True, timeout=60 * 5):
        return {"queued": False, "reason": "already_recently_requested"}

    try:
        end_dt = timezone.now()
        start_dt = end_dt - timedelta(days=int(lookback_days or 10))

        repo = get_repository()
        repo.ensure_complete(
            symbol=normalized_symbol,
            canonical_timeframe=tf,
            start=start_dt,
            end=end_dt,
        )
        return {
            "queued": True,
            "symbol": normalized_symbol,
            "resolution": tf,
            "status": "completed",
        }
    except (DataIncompleteError, BrokerError) as exc:
        logger.warning("backfill_missing_candles incomplete for %s: %s", normalized_symbol, exc)
        return {"queued": True, "status": "incomplete", "error": str(exc)}
    except Exception as exc:
        logger.exception("backfill_missing_candles failed for %s: %s", normalized_symbol, exc)
        return {"queued": True, "status": "error", "error": str(exc)}
    finally:
        cache.delete(lock_key)


@shared_task(name="marketdata.fetch_live_candles_from_broker")
def fetch_live_candles_from_broker():
    """
    Minute reconciliation: fetch the most recent finalised 1m candles from
    FYERS for all actively tracked symbols and upsert them.

    This replaces the local tick-based candle aggregator with broker-finalised
    historical data.  Uses a per-symbol lock to prevent overlapping runs.

    Behaviour per symbol:
      1. Find the latest finalised 1m candle in DB.
      2. Fetch from (latest − 2 min) to (now − 1 min) — the forming minute
         is excluded because it is not yet finalised.
      3. Upsert any returned candles.
      4. Repair missed minutes after outages.
    """
    from .streaming import MarketDataStreamer
    from types import SimpleNamespace

    symbols = LiveMarketDataRegistry.get_symbols()
    if not symbols:
        return {"fetched_symbols": 0}

    now = timezone.now()
    # Exclude the currently-forming minute (broker won't have it finalised yet)
    reconcile_end = now - timedelta(minutes=1)

    fetched_count = 0
    for symbol in symbols:
        lock_key = f"marketdata:live_reconcile:{symbol}"
        if not cache.add(lock_key, True, timeout=_RECONCILE_LOCK_TTL):
            logger.debug("Skipping live reconcile for %s — already running", symbol)
            continue

        try:
            # Determine the overlap start point
            latest = MarketDataService.latest_candle(symbol, "1m")
            if latest:
                # Fetch with a 2-minute overlap to catch any missed candles
                fetch_start = latest.time - timedelta(minutes=2)
            else:
                # No data at all — fetch last 5 minutes
                fetch_start = reconcile_end - timedelta(minutes=5)

            fetched = MarketDataService.backfill_candles_from_broker(
                symbol=symbol,
                date_from=fetch_start.isoformat(),
                date_to=reconcile_end.isoformat(),
                timeframe="1m",
            )

            if fetched is None:
                logger.warning("FYERS returned error during live reconcile for %s", symbol)
                continue

            if fetched:
                latest_candle = fetched[-1]
                candle_obj = SimpleNamespace(**latest_candle)
                MarketDataStreamer.publish_candle_update(
                    symbol, candle_obj, event_type="candle.closed"
                )
                fetched_count += 1

        except Exception as exc:
            logger.exception(
                "Failed fetching live candles from broker for %s: %s", symbol, exc
            )
        finally:
            cache.delete(lock_key)

    return {"fetched_symbols": fetched_count}


@shared_task(name="marketdata.reconcile_daily_market_data")
def reconcile_daily_market_data():
    """
    End-of-day reconciliation task.

    SAFETY CONTRACT: canonical historical data is NEVER deleted solely
    because a broker API call returns no data.  Possible reasons for an
    empty response include:
      - Actual holiday / non-trading day (expected).
      - Broker API error.
      - Auth/token failure.
      - Network error.
      - Broker temporarily unavailable.

    Only a CONFIRMED non-trading day (validated via TradingCalendar + a
    successful API call that explicitly says "no_data") results in any action,
    and even then we do NOT delete existing candles — we simply log the result.

    The old "delete all today's candles when benchmark returns empty" behaviour
    has been removed because it could silently destroy valid market data on
    any broker outage.
    """
    now = timezone.now()
    today = now.date()

    benchmark_symbol = "NSE:NIFTY50-INDEX"

    # Check if today is even a trading day first
    try:
        trading_days = TradingCalendar.trading_days(today, today)
        if not trading_days:
            logger.info(
                "Daily reconciliation: %s is a weekend or holiday — no action required.",
                today,
            )
            return {"status": "non_trading_day", "date": str(today)}
    except Exception as exc:
        logger.warning("Could not check trading calendar: %s — proceeding with caution", exc)

    # Attempt to fetch today's 1D candle for the benchmark as a health check
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        fetched = MarketDataService.fetch_candles_from_broker(
            symbol=benchmark_symbol,
            timeframe="1D",
            date_from=start_dt.isoformat(),
            date_to=now.isoformat(),
        )
    except Exception as exc:
        logger.exception("Daily reconciliation: broker fetch failed: %s", exc)
        # DO NOT delete data on a fetch failure.
        return {"status": "error", "error": str(exc), "deleted": 0}

    if fetched is None:
        # API error (not "no_data") — broker failure, token expiry, network, etc.
        # Treat as a health check failure; do NOT touch canonical data.
        logger.error(
            "Daily reconciliation: FYERS returned an API error for benchmark %s. "
            "No data will be modified.",
            benchmark_symbol,
        )
        return {"status": "broker_error", "deleted": 0}

    if fetched:
        # Benchmark traded today — upsert its candle and report success.
        MarketDataService.upsert_candles(benchmark_symbol, "1D", fetched)
        logger.info(
            "Daily reconciliation: benchmark %s traded today (%d candle(s)). "
            "All canonical data preserved.",
            benchmark_symbol, len(fetched),
        )
        return {"status": "official_session_kept", "deleted": 0}

    # fetched == [] means FYERS confirmed "no_data" for this date.
    # This is a valid non-trading day according to the broker.
    # Log it, but DO NOT delete existing canonical candles — they may be from
    # pre-market, a partial session, or an error in the original detection.
    logger.info(
        "Daily reconciliation: FYERS returned no data for benchmark %s on %s. "
        "Treating as non-trading day.  Existing canonical candles are preserved.",
        benchmark_symbol, today,
    )
    return {"status": "no_data_non_trading_day", "deleted": 0, "date": str(today)}
