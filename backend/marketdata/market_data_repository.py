"""
MarketDataRepository — canonical market-data access layer.

All consumers (Chart, Backtest, Strategy, Analytics, Paper, Live) MUST use
``MarketDataRepository.get_candles()`` instead of calling low-level DB or
broker helpers directly.

Guarantees:
  1. Only 1m and 1D candles are stored; all other timeframes are derived.
  2. Exact coverage validation via TradingCalendar before any data is served.
  3. Missing ranges are fetched from FYERS (minimal fetch — only gaps).
  4. FYERS API errors raise BrokerError — never silently return empty data.
  5. Data is never returned as complete when a gap remains.

Exceptions
----------
DataIncompleteError   — gaps remain and cannot be repaired synchronously.
DataNotAvailableError — broker confirmed no data (valid non-trading day).
BrokerError           — broker API failure (auth, network, etc.).
"""
from __future__ import annotations

import logging
import time as _time
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
from django.core.cache import cache
from django.utils import timezone

from instruments.models import Instrument

from .models import CANONICAL_TIMEFRAMES, Candle
from .trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)

# Maximum days fetchable synchronously. Larger requests raise DataIncompleteError
# so the caller can enqueue an async backfill instead.
MAX_SYNC_DAYS = 120

# Distributed lock TTL (seconds) preventing concurrent duplicate fetches.
FETCH_LOCK_TTL = 30

# Pandas resample frequency strings for derived timeframes.
_PANDAS_FREQ: Dict[str, str] = {
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1H": "1h",
    "4H": "4h",
    "1W": "1W",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DataIncompleteError(Exception):
    """Raised when data cannot be verified complete before serving."""

    def __init__(self, symbol: str, timeframe: str, missing_count: int = 0, message: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.missing_count = missing_count
        super().__init__(
            message or f"Data incomplete for {symbol} {timeframe}: {missing_count} missing candle(s)"
        )


class DataNotAvailableError(Exception):
    """Raised when the broker confirmed no data for the requested window."""

    def __init__(self, symbol: str, timeframe: str, reason: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.reason = reason
        super().__init__(f"No data available for {symbol} {timeframe}: {reason}")


class BrokerError(Exception):
    """Raised when the broker API returns a failure (not a valid empty response)."""

    def __init__(self, symbol: str, timeframe: str, detail: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.detail = detail
        super().__init__(f"Broker error for {symbol} {timeframe}: {detail}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical_for(timeframe: str) -> str:
    """
    Return the canonical backing timeframe for *timeframe*.

      1m  → 1m
      1D  → 1D
      1W  → 1D  (weekly derives from daily)
      any intraday derived → 1m
    """
    if timeframe in CANONICAL_TIMEFRAMES:
        return timeframe
    if timeframe == "1W":
        return "1D"
    return "1m"


def _coerce_utc(value, start_of_day: bool = True) -> datetime:
    """Coerce a date, datetime, or None to a UTC-aware datetime."""
    if value is None:
        return timezone.now()
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return value.replace(tzinfo=dt_timezone.utc)
        return value.astimezone(dt_timezone.utc)
    if isinstance(value, date):
        t = time.min if start_of_day else time.max
        return datetime.combine(value, t, tzinfo=dt_timezone.utc)
    raise TypeError(f"Cannot coerce {value!r} to UTC datetime")


def _fetch_lock_key(symbol: str, canonical_tf: str, start: date, end: date) -> str:
    return f"mdrepo:fetch_lock:{symbol}:{canonical_tf}:{start.isoformat()}:{end.isoformat()}"


def _db_actual_timestamps(
    symbol: str, canonical_tf: str, start_dt: datetime, end_dt: datetime
) -> List[datetime]:
    """Return all stored candle timestamps (UTC) for the given window."""
    qs = (
        Candle.objects.filter(
            symbol=symbol,
            timeframe=canonical_tf,
            time__gte=start_dt,
            time__lte=end_dt,
        )
        .values_list("time", flat=True)
        .order_by("time")
    )
    result = []
    for ts in qs:
        ts = ts.replace(tzinfo=dt_timezone.utc) if ts.tzinfo is None else ts
        result.append(ts.astimezone(dt_timezone.utc))
    return result





# ---------------------------------------------------------------------------
# Coverage check result
# ---------------------------------------------------------------------------

class CoverageResult:
    """Result of an exact coverage check against TradingCalendar."""

    __slots__ = ("complete", "expected", "actual_set", "missing", "fetch_ranges")

    def __init__(
        self,
        complete: bool,
        expected: List[datetime],
        actual_set: List[datetime],
        missing: List[datetime],
        fetch_ranges: List[Tuple[datetime, datetime]],
    ):
        self.complete = complete
        self.expected = expected
        self.actual_set = actual_set
        self.missing = missing
        self.fetch_ranges = fetch_ranges


def _check_coverage(
    symbol: str,
    canonical_tf: str,
    start_dt: datetime,
    end_dt: datetime,
) -> CoverageResult:
    """
    Compare TradingCalendar expected timestamps against actual DB rows.

    Returns a CoverageResult describing any gaps and the fetch ranges needed
    to repair them.
    """
    start_date = start_dt.date()
    end_date = end_dt.date()

    expected = TradingCalendar.expected_timestamps(canonical_tf, start_date, end_date)
    actual = _db_actual_timestamps(symbol, canonical_tf, start_dt, end_dt)
    missing = TradingCalendar.find_missing_timestamps(expected, actual)
    fetch_ranges = TradingCalendar.merge_to_ranges(missing)

    return CoverageResult(
        complete=len(missing) == 0,
        expected=expected,
        actual_set=actual,
        missing=missing,
        fetch_ranges=fetch_ranges,
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class MarketDataRepository:
    """
    Single entry point for all historical market data access.

    Example
    -------
    ::

        repo = get_repository()
        candles = repo.get_candles(
            symbol="NSE:SBIN-EQ",
            timeframe="15m",
            start=date(2025, 1, 1),
            end=date(2025, 3, 31),
        )

    Flow inside get_candles:
      1. Resolve canonical backing timeframe.
      2. Exact coverage check vs TradingCalendar.
      3. Fetch only missing ranges from FYERS.
      4. Re-verify after upsert.
      5. Raise DataIncompleteError / BrokerError if gaps remain.
      6. Aggregate to requested timeframe if derived.
      7. Return serialised candle dicts.
    """

    def get_candles(
        self,
        *,
        instrument: Optional[Instrument] = None,
        symbol: Optional[str] = None,
        timeframe: str,
        start,
        end,
        ensure_complete: bool = True,
        allow_partial: bool = False,
    ) -> List[dict]:
        """
        Fetch candles for *instrument* or *symbol* at *timeframe* in [start, end].

        Parameters
        ----------
        instrument      : Instrument ORM object (preferred over symbol).
        symbol          : Fyers ticker string (fallback).
        timeframe       : Any supported timeframe (1m, 5m, 15m, 1H, 1D, 1W …).
        start / end     : date or datetime.
        ensure_complete : Detect and repair gaps before returning (default True).
        allow_partial   : When True, return whatever is in the DB even if gaps
                          remain after a FYERS fetch attempt (e.g. partial previews).

        Returns
        -------
        List[dict] with keys: time, open, high, low, close, volume.

        Raises
        ------
        DataIncompleteError   — gaps remain and ensure_complete is True.
        BrokerError           — FYERS API returned an error during repair.
        ValueError            — invalid timeframe or no symbol/instrument given.
        """
        from .services import MarketDataService

        if instrument is not None:
            sym = instrument.sym_ticker
        elif symbol:
            sym = MarketDataService.normalize_symbol(symbol)
        else:
            raise ValueError("Either instrument or symbol must be provided")

        tf = MarketDataService.normalize_timeframe(timeframe)
        canonical_tf = _canonical_for(tf)

        start_dt = _coerce_utc(start, start_of_day=True)
        end_dt = _coerce_utc(end, start_of_day=False)
        end_dt = min(end_dt, timezone.now())  # never request future data

        if instrument is None:
            try:
                instrument = Instrument.objects.filter(sym_ticker=sym).first()
            except Exception:
                instrument = None

        if ensure_complete:
            self._ensure_complete(sym, canonical_tf, start_dt, end_dt, allow_partial)

        raw_candles = self._load_from_db(sym, canonical_tf, start_dt, end_dt)

        if tf != canonical_tf:
            return self._aggregate(raw_candles, tf)

        from .services import MarketDataService
        return [MarketDataService.serialize_candle(c) for c in raw_candles]

    def _ensure_complete(
        self,
        sym: str,
        canonical_tf: str,
        start_dt: datetime,
        end_dt: datetime,
        allow_partial: bool,
    ) -> None:
        """
        Verify exact coverage and fetch missing ranges from FYERS.
        Re-verifies after upsert.  Raises if gaps remain (unless allow_partial).
        """
        from .services import MarketDataService

        days_requested = max(1, (end_dt.date() - start_dt.date()).days + 1)
        if days_requested > MAX_SYNC_DAYS:
            raise DataIncompleteError(
                sym, canonical_tf,
                message=(
                    f"Range ({days_requested} days) exceeds synchronous limit "
                    f"({MAX_SYNC_DAYS} days). Enqueue an async backfill first."
                ),
            )

        coverage = _check_coverage(sym, canonical_tf, start_dt, end_dt)
        if coverage.complete:
            return

        logger.info(
            "Coverage gap for %s %s: %d missing candle(s) across %d range(s)",
            sym, canonical_tf, len(coverage.missing), len(coverage.fetch_ranges),
        )

        lock_key = _fetch_lock_key(sym, canonical_tf, start_dt.date(), end_dt.date())
        if not cache.add(lock_key, True, timeout=FETCH_LOCK_TTL):
            # Another thread is already fetching — wait briefly then re-check.
            _time.sleep(2)
            coverage = _check_coverage(sym, canonical_tf, start_dt, end_dt)
            if coverage.complete:
                return

        try:
            any_broker_error = False
            for range_start, range_end in coverage.fetch_ranges:
                result = MarketDataService.fetch_candles_from_broker(
                    sym, canonical_tf,
                    range_start.date().isoformat(),
                    range_end.date().isoformat(),
                )
                if result is None:
                    any_broker_error = True
                    logger.error(
                        "FYERS API error for gap %s → %s (%s %s)",
                        range_start.date(), range_end.date(), sym, canonical_tf,
                    )
                elif result:
                    MarketDataService.upsert_candles(sym, canonical_tf, result)
                # result == [] means valid no_data (holiday/weekend) — not an error
        finally:
            cache.delete(lock_key)

        coverage = _check_coverage(sym, canonical_tf, start_dt, end_dt)
        if coverage.complete:
            return

        remaining = len(coverage.missing)
        if any_broker_error:
            raise BrokerError(
                sym, canonical_tf,
                detail=f"Broker API error; {remaining} candle(s) still missing",
            )

        logger.warning(
            "After FYERS fetch, %d candle(s) still missing for %s %s "
            "(may be intra-session gaps the broker has no record of).",
            remaining, sym, canonical_tf,
        )
        if not allow_partial:
            raise DataIncompleteError(sym, canonical_tf, missing_count=remaining)

    def _load_from_db(
        self, sym: str, canonical_tf: str, start_dt: datetime, end_dt: datetime
    ) -> List[Candle]:
        return list(
            Candle.objects.filter(
                symbol=sym,
                timeframe=canonical_tf,
                time__gte=start_dt,
                time__lte=end_dt,
            ).order_by("time")
        )

    def _aggregate(self, raw_candles: List[Candle], target_tf: str) -> List[dict]:
        """Aggregate canonical candles to a derived timeframe using pandas resample."""
        if not raw_candles:
            return []

        freq = _PANDAS_FREQ.get(target_tf)
        if not freq:
            raise ValueError(f"Cannot aggregate to timeframe {target_tf!r}")

        rows = [
            {
                "time": c.time if c.time.tzinfo else c.time.replace(tzinfo=dt_timezone.utc),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": int(c.volume or 0),
            }
            for c in raw_candles
        ]

        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.set_index("time").sort_index()

        agg = df.resample(freq, closed="left", label="left").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna(subset=["open"])

        return [
            {
                "time": int(ts.timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"] or 0),
            }
            for ts, row in agg.iterrows()
        ]

    # ------------------------------------------------------------------
    # Convenience method for backfill jobs
    # ------------------------------------------------------------------

    def ensure_complete(
        self,
        *,
        instrument: Optional[Instrument] = None,
        symbol: Optional[str] = None,
        canonical_timeframe: str,
        start,
        end,
    ) -> None:
        """
        Ensure canonical data is complete for [start, end].
        Does not return candles — use from backfill tasks.

        Raises BrokerError or DataIncompleteError if gaps cannot be repaired.
        """
        from .services import MarketDataService

        if instrument is not None:
            sym = instrument.sym_ticker
        elif symbol:
            sym = MarketDataService.normalize_symbol(symbol)
        else:
            raise ValueError("Either instrument or symbol must be provided")

        if canonical_timeframe not in CANONICAL_TIMEFRAMES:
            raise ValueError(f"{canonical_timeframe!r} is not a canonical timeframe")

        start_dt = _coerce_utc(start, start_of_day=True)
        end_dt = min(_coerce_utc(end, start_of_day=False), timezone.now())

        self._ensure_complete(sym, canonical_timeframe, start_dt, end_dt, allow_partial=False)

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_repository: Optional[MarketDataRepository] = None


def get_repository() -> MarketDataRepository:
    """Return the module-level MarketDataRepository singleton."""
    global _repository
    if _repository is None:
        _repository = MarketDataRepository()
    return _repository
