"""
Trading Calendar — session-aware expected-candle generator.

Single authority for "what timestamps should exist" for a given
symbol/timeframe/date range.  Nothing else should compute expected-candle sets.

Session rules (NSE equity):
  - 1m candles: Mon–Fri 09:15–15:29 IST, excluding holidays.
  - 1D candles: one per trading day, aligned to midnight UTC.
  - India has no DST; IST = UTC+5:30 permanently.

A weekend or declared NSE_HOLIDAY is never reported as missing data.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import List, Set

import pytz
from django.core.cache import cache

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# NSE cash-equity intraday session boundaries (IST).
NSE_SESSION_START = time(9, 15)
NSE_SESSION_LAST_OPEN = time(15, 29)  # last 1m bar opens here, closes at 15:30

# Full NSE equity session = 375 minutes (09:15 .. 15:29 inclusive).
NSE_1M_CANDLES_PER_DAY = 375

_HOLIDAY_CACHE_KEY = "trading_calendar:nse_holidays"
_HOLIDAY_CACHE_TTL = 86400  # 24 h


# ---------------------------------------------------------------------------
# Holiday registry
# ---------------------------------------------------------------------------

def get_nse_holidays() -> Set[date]:
    """
    Return the set of NSE-declared holidays from the MarketEvent table
    (event_type='NSE_HOLIDAY').  Results are cached for 24 h.
    Falls back to an empty set if the table has no data.
    """
    cached = cache.get(_HOLIDAY_CACHE_KEY)
    if cached is not None:
        return set(cached)

    holidays: Set[date] = set()
    try:
        from .models import MarketEvent
        holidays = set(
            MarketEvent.objects.filter(event_type="NSE_HOLIDAY")
            .values_list("event_date", flat=True)
        )
    except Exception as exc:
        logger.warning("Could not load NSE holidays from DB: %s", exc)

    cache.set(_HOLIDAY_CACHE_KEY, list(holidays), timeout=_HOLIDAY_CACHE_TTL)
    return holidays


def invalidate_holiday_cache() -> None:
    """Force the next get_nse_holidays() call to re-query the DB."""
    cache.delete(_HOLIDAY_CACHE_KEY)


def is_trading_day(d: date, holidays: Set[date] | None = None) -> bool:
    """Return True if *d* is a normal NSE equity trading day (weekday, not a holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if holidays is None:
        holidays = get_nse_holidays()
    return d not in holidays


# ---------------------------------------------------------------------------
# Per-date timestamp generators (private helpers)
# ---------------------------------------------------------------------------

def _session_1m_timestamps_for_date(d: date) -> List[datetime]:
    """
    All expected 1m candle open timestamps (UTC-aware) for one NSE trading day.
    Returns [] for weekends and holidays.
    """
    if not is_trading_day(d):
        return []

    timestamps: List[datetime] = []
    current = datetime.combine(d, NSE_SESSION_START, tzinfo=IST)
    end = datetime.combine(d, NSE_SESSION_LAST_OPEN, tzinfo=IST)
    while current <= end:
        timestamps.append(current.astimezone(dt_timezone.utc))
        current += timedelta(minutes=1)
    return timestamps


def _session_1d_timestamp_for_date(d: date) -> datetime | None:
    """
    Expected 1D candle timestamp (midnight UTC) for one NSE trading day.
    Returns None for weekends and holidays.
    """
    if not is_trading_day(d):
        return None
    return datetime.combine(d, time.min, tzinfo=dt_timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TradingCalendar:
    """
    Centralised session/calendar service.

    All market-data completeness checks use this class so that holiday logic,
    session rules, and timezone handling live in exactly one place.
    """

    @staticmethod
    def expected_1m_timestamps(start_date: date, end_date: date) -> List[datetime]:
        """Sorted UTC timestamps for all expected 1m candles in [start_date, end_date]."""
        result: List[datetime] = []
        d = start_date
        while d <= end_date:
            result.extend(_session_1m_timestamps_for_date(d))
            d += timedelta(days=1)
        return result

    @staticmethod
    def expected_1d_timestamps(start_date: date, end_date: date) -> List[datetime]:
        """Sorted UTC timestamps for all expected 1D candles in [start_date, end_date]."""
        result: List[datetime] = []
        d = start_date
        while d <= end_date:
            ts = _session_1d_timestamp_for_date(d)
            if ts:
                result.append(ts)
            d += timedelta(days=1)
        return result

    @staticmethod
    def expected_timestamps(
        canonical_timeframe: str, start_date: date, end_date: date
    ) -> List[datetime]:
        """
        Dispatch to expected_1m_timestamps or expected_1d_timestamps.
        Raises ValueError for non-canonical timeframes.
        """
        if canonical_timeframe == "1m":
            return TradingCalendar.expected_1m_timestamps(start_date, end_date)
        if canonical_timeframe == "1D":
            return TradingCalendar.expected_1d_timestamps(start_date, end_date)
        raise ValueError(
            f"expected_timestamps() only accepts canonical timeframes (1m, 1D); "
            f"got {canonical_timeframe!r}"
        )

    @staticmethod
    def trading_days(start_date: date, end_date: date) -> List[date]:
        """List of NSE equity trading days in [start_date, end_date] (inclusive)."""
        holidays = get_nse_holidays()
        result: List[date] = []
        d = start_date
        while d <= end_date:
            if is_trading_day(d, holidays):
                result.append(d)
            d += timedelta(days=1)
        return result

    @staticmethod
    def find_missing_timestamps(
        expected: List[datetime], actual: List[datetime]
    ) -> List[datetime]:
        """
        Return every timestamp in *expected* that is absent from *actual*.

        Uses a set difference — detects gaps anywhere in the session, not just
        at the first or last candle.  Both lists must be UTC-aware.
        """
        actual_set: Set[datetime] = set()
        for ts in actual:
            ts = ts.replace(tzinfo=dt_timezone.utc) if ts.tzinfo is None else ts.astimezone(dt_timezone.utc)
            actual_set.add(ts)

        missing: List[datetime] = []
        for ts in expected:
            ts = ts.replace(tzinfo=dt_timezone.utc) if ts.tzinfo is None else ts.astimezone(dt_timezone.utc)
            if ts not in actual_set:
                missing.append(ts)

        return sorted(missing)

    @staticmethod
    def merge_to_ranges(
        missing_timestamps: List[datetime],
        gap_tolerance_minutes: int = 2,
    ) -> List[tuple[datetime, datetime]]:
        """
        Collapse a sorted list of missing timestamps into contiguous fetch ranges.

        Two consecutive missing timestamps are merged into one range when the
        gap between them is <= gap_tolerance_minutes + 1 minutes.
        """
        if not missing_timestamps:
            return []

        ranges: List[tuple[datetime, datetime]] = []
        window_start = missing_timestamps[0]
        window_end = missing_timestamps[0]

        for ts in missing_timestamps[1:]:
            gap = (ts - window_end).total_seconds() / 60
            if gap <= gap_tolerance_minutes + 1:
                window_end = ts
            else:
                ranges.append((window_start, window_end))
                window_start = ts
                window_end = ts

        ranges.append((window_start, window_end))
        return ranges

    @staticmethod
    def candles_per_day(canonical_timeframe: str) -> int:
        """Expected candle count for a complete trading day."""
        if canonical_timeframe == "1m":
            return NSE_1M_CANDLES_PER_DAY
        if canonical_timeframe == "1D":
            return 1
        raise ValueError(f"Not a canonical timeframe: {canonical_timeframe!r}")
