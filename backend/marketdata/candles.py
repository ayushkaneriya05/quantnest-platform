"""Shared historical reads and pure candle aggregation, including live observations."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

import numpy as np
import pandas as pd

from .contracts import CandleRequest, HistoryRequest, OHLCV, interval_minutes, source_timeframe


def candle_frame(rows: list[dict]) -> pd.DataFrame:
    """Transport/buffer rows use epoch seconds; analytical indices use UTC openings."""
    frame = pd.DataFrame(rows, columns=["time", *OHLCV])
    frame.index = pd.to_datetime(frame.pop("time"), unit="s", utc=True)
    return frame.loc[~frame.index.duplicated(keep="last")].sort_index()


def available_frame(frame: pd.DataFrame, timeframe: str, calendar) -> pd.DataFrame:
    result = frame.loc[:, list(OHLCV)].copy()
    result.index = pd.DatetimeIndex([calendar.candle_close(stamp.to_pydatetime(), timeframe)
                                    for stamp in frame.index], tz="UTC", name="timestamp")
    return result


def aggregate_candles(data: pd.DataFrame, timeframe: str, calendar, as_of: datetime, *,
                      source: str = "1m", include_open: bool = False) -> pd.DataFrame:
    """One OHLCV definition for charts, research, historical and live calculation.

    Sparse source observations stay sparse. Acquisition completeness is checked
    separately; absence of a trade does not create a synthetic price.
    """
    columns = [*OHLCV, "source_end", "available_at", "is_final"]
    if data.empty:
        return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], tz="UTC"))
    minutes = interval_minutes(timeframe)
    seconds = data.index.as_unit("s").asi8
    buckets, visible = np.zeros(len(data), dtype=np.int64), np.zeros(len(data), dtype=bool)
    first = calendar.session_bounds(data.index[0])[0].date()
    last = data.index[-1].astimezone(calendar.zone).date()
    # Assign integer buckets in place. Build one DataFrame, rather than slicing
    # and copying a DataFrame for every trading day and session break.
    for day in calendar._date_range(first, last):
        if not calendar.is_trading_day(day):
            continue
        periods = ((calendar.session_open(day), calendar.session_close(day)),) if source == "1D" else calendar.trading_periods(day)
        for opening, closing in periods:
            if source == "1D" and closing > as_of and not include_open:
                continue
            left, right = np.searchsorted(seconds, [int(opening.timestamp()), int(closing.timestamp())])
            if left == right:
                continue
            values = seconds[left:right]
            if minutes:
                step, anchor = minutes * 60, int(opening.timestamp())
                buckets[left:right] = anchor + ((values - anchor) // step) * step
            else:
                buckets[left:right] = int(calendar.bucket_start(opening, timeframe).timestamp())
            visible[left:right] = (True if source == "1D" else
                                   values <= as_of.timestamp() if include_open else values + 60 <= as_of.timestamp())
    if not visible.any():
        return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], tz="UTC"))
    frame = data.loc[visible, list(OHLCV)].assign(bucket=buckets[visible], source_end=seconds[visible]).groupby("bucket").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"), source_end=("source_end", "max"),
    )
    frame.index = pd.to_datetime(frame.index, unit="s", utc=True)
    frame["available_at"] = [int(calendar.candle_close(stamp.to_pydatetime(), timeframe).timestamp())
                             for stamp in frame.index]
    frame["is_final"] = frame["available_at"] <= as_of.timestamp()
    return frame if include_open else frame.loc[frame["is_final"]]


def build_frames(sources: dict[str, pd.DataFrame], timeframes: frozenset[str], calendar,
                 as_of: datetime) -> dict[str, pd.DataFrame]:
    """Pure calculation entry point; no database, provider or cache access."""
    return {tf: aggregate_candles(sources[source_timeframe(tf)], tf, calendar, as_of,
                                 source=source_timeframe(tf)).loc[:, list(OHLCV)]
            for tf in sorted(timeframes) if source_timeframe(tf) in sources}


@dataclass
class CandleBatch:
    frame: pd.DataFrame
    quality: dict

    def records(self) -> list[dict]:
        return [
            {"time": int(stamp.timestamp()), **{key: float(row[key]) for key in OHLCV[:4]},
             "volume": int(row["volume"]), "source_end": int(row["source_end"]),
             "available_at": int(row["available_at"]), "is_final": bool(row["is_final"]),
             "source": "provider", "revision": self.quality["updated_at"]}
            for stamp, row in self.frame.iterrows()
        ]


def read_source_data(request: HistoryRequest) -> tuple[pd.DataFrame, float]:
    """Read confirmed rows and their latest update time from a completed source range.

    Callers normalize the range with completed_request before reading. Coverage
    statistics are separate so live chart preparation does not calculate them.
    """
    from django.conf import settings
    from .models import Candle

    queryset = Candle.objects.filter(
        symbol=request.instrument.sym_ticker, provider=settings.MARKET_DATA_PROVIDER,
        timeframe=request.timeframe, provider_confirmed=True,
        time__gte=request.start, time__lt=request.end,
    ).order_by("time").values_list("time", *OHLCV, "updated_at")
    frame = pd.DataFrame.from_records(queryset.iterator(chunk_size=10000), columns=["time", *OHLCV, "updated_at"])
    updated_at = max((stamp.timestamp() for stamp in frame.pop("updated_at")), default=0)
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop("time"), utc=True), name="time")
    frame = frame.astype({key: "float64" for key in OHLCV[:4]} | {"volume": "int64"})
    return frame, updated_at


def read_source(request: HistoryRequest) -> CandleBatch:
    """Read source rows with acquisition coverage for historical/analytical callers."""
    from .history import completed_request, missing_history, data_revision

    request = completed_request(request)
    frame, updated_at = read_source_data(request)
    gaps = missing_history(request)
    expected = request.calendar.source_count(request.timeframe, request.start, request.end)
    quality = {
        "source_timeframe": request.timeframe, "complete": not gaps,
        "available_count": len(frame), "expected_count": expected,
        "missing_count": max(0, expected - len(frame)), "sparse": len(frame) < expected,
        "pending_ranges": [[left.isoformat(), right.isoformat()] for left, right in gaps],
        "revision": data_revision(request.instrument.sym_ticker), "updated_at": updated_at, "empty": frame.empty,
    }
    return CandleBatch(frame, quality)


def read_candles(request: CandleRequest) -> CandleBatch:
    """Bounded read only. Call ensure_history explicitly to acquire missing data."""
    from django.conf import settings
    from django.core.cache import cache
    from django.utils import timezone as django_timezone
    from .history import data_revision

    calendar = request.calendar
    calendar.load_holidays(request.start.astimezone(calendar.zone).date() - timedelta(days=7),
                           request.end.astimezone(calendar.zone).date() + timedelta(days=31))
    revision = data_revision(request.instrument.sym_ticker)
    # Historical reads only see completed source minutes. Active observations are
    # published separately, so repeated chart opens share a stable read window.
    source = source_timeframe(request.timeframe)
    as_of = min(request.end, django_timezone.now())
    end = max(request.start, datetime.fromtimestamp(calendar.completed_horizon(source, as_of), as_of.tzinfo))
    identity = (settings.MARKET_DATA_PROVIDER, request.instrument.sym_ticker, request.timeframe, request.start.isoformat(),
                end.isoformat(), request.limit, request.include_open, revision, calendar.signature)
    key = "marketdata:candles:" + hashlib.sha256(repr(identity).encode()).hexdigest()
    stored = cache.get(key)
    if stored is not None:
        return stored
    batch = read_source(HistoryRequest(request.instrument, source, request.start, max(request.start, end), calendar))
    batch.frame = aggregate_candles(batch.frame, request.timeframe, calendar, end, source=source,
                                    include_open=request.include_open)
    if request.limit:
        batch.frame = batch.frame.tail(request.limit)
    # Provider writes change the revision. Briefly cache pending/empty reads too.
    cache.set(key, batch, 30 if batch.quality["complete"] else 5)
    return batch


def prepare_frames(instrument, timeframes: frozenset[str], windows: dict, calendar):
    """Prepare each source once; callers supply requirements rather than rule JSON."""
    from .history import ensure_history

    sources, quality = {}, {}
    for source, (start, end) in sorted(windows.items()):
        request = HistoryRequest(instrument, source, start, end, calendar)
        result = ensure_history(request)
        batch = read_source(request)
        sources[source] = batch.frame
        quality[source] = {**batch.quality, "fetched": result.fetched, "error": result.error,
                           "complete": result.complete and batch.quality["complete"]}
    as_of = max(end for _, end in windows.values())
    frames = build_frames(sources, timeframes, calendar, as_of)
    return frames, {
        "instrument": instrument.sym_ticker, "complete": all(item["complete"] for item in quality.values()),
        "timeframes": {tf: quality[source_timeframe(tf)] for tf in timeframes},
    }
