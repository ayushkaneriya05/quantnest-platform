"""The only historical acquisition/writing path, shared by all application features."""
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone as django_timezone
from redis.exceptions import LockError, RedisError

from common.redis import runtime_redis
from instruments.models import Instrument
from .contracts import HistoryRequest, HistoryResult, OHLCV, ProviderError, valid_candle
from .models import Candle, HistoryCoverage

logger = logging.getLogger(__name__)
RECENT_HISTORY = timedelta(days=1)
RECHECK_DELAY = timedelta(minutes=5)


def revision_key(symbol: str) -> str:
    return f"quantnest:data-revision:{settings.MARKET_DATA_PROVIDER}:{symbol}"


def data_revision(symbol: str) -> int:
    return int(runtime_redis().get(revision_key(symbol)) or 0)


def publish_revision(symbol: str):
    # Cache publication must not turn a committed ingestion into an API failure.
    # Readers also have bounded cache lifetimes and periodically reload their buffers.
    try:
        runtime_redis().incr(revision_key(symbol))
    except RedisError:
        logger.exception("Could not publish history revision symbol=%s", symbol)


def completed_request(request: HistoryRequest) -> HistoryRequest:
    calendar = request.calendar
    end = min(request.end, django_timezone.now())
    calendar.load_holidays(request.start.astimezone(calendar.zone).date() - timedelta(days=7),
                           end.astimezone(calendar.zone).date() + timedelta(days=31))
    expiry = request.instrument.expiry_date
    if expiry is not None:
        end = min(end, calendar.session_close(expiry))
    if request.timeframe == "1m":
        end = end.replace(second=0, microsecond=0)
    else:
        end = min(end, datetime.fromtimestamp(calendar.completed_horizon("1D", end), timezone.utc))
    return replace(request, end=max(request.start, end))


def _trading_range(request: HistoryRequest, start: datetime, end: datetime):
    """Trim non-trading edges without manufacturing candles inside sparse sessions."""
    calendar = request.calendar
    ranges = []
    day = calendar.session_bounds(start)[0].date()
    for day in calendar._date_range(day, end.astimezone(calendar.zone).date()):
        if not calendar.is_trading_day(day):
            continue
        if request.timeframe == "1D":
            opening, closing = calendar.session_open(day), calendar.session_close(day)
            if start <= opening < end and closing <= request.end:
                ranges.append((opening, closing))
        else:
            ranges.extend((max(left, start), min(right, end))
                          for left, right in calendar.trading_periods(day)
                          if max(left, start) < min(right, end))
    return (ranges[0][0], ranges[-1][1]) if ranges else None


def missing_history(request: HistoryRequest) -> list[tuple[datetime, datetime]]:
    """Acquisition coverage, independent of the number of returned candle rows."""
    now = django_timezone.now()
    rows = HistoryCoverage.objects.filter(
        instrument=request.instrument, provider=settings.MARKET_DATA_PROVIDER,
        timeframe=request.timeframe, end__gt=request.start, start__lt=request.end,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).order_by("start")
    cursor, gaps = request.start, []
    for left, right in rows.values_list("start", "end"):
        if left > cursor:
            gaps.append((cursor, min(left, request.end)))
        cursor = max(cursor, right)
    if cursor < request.end:
        gaps.append((cursor, request.end))
    return [window for left, right in gaps if (window := _trading_range(request, left, right))]


def _prepare_rows(request: HistoryRequest, candles: list[dict]) -> list[dict]:
    calendar = request.calendar
    unique = {}
    for candle in candles:
        try:
            stamp = candle["time"]
            valid = isinstance(stamp, datetime) and stamp.utcoffset() is not None and valid_candle(candle)
        except (KeyError, TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            raise ProviderError(f"Invalid historical candle for {request.instrument.sym_ticker}.")
        if request.timeframe == "1D":
            stamp = calendar.session_open(stamp.astimezone(calendar.zone).date())
        elif stamp.second or stamp.microsecond:
            raise ProviderError(f"Unaligned historical minute for {request.instrument.sym_ticker}.")
        if (request.start <= stamp < request.end and calendar.is_open(stamp)
                and calendar.candle_close(stamp, request.timeframe) <= request.end):
            unique[stamp] = {
                "time": stamp.astimezone(timezone.utc),
                **{key: Decimal(str(candle[key])).quantize(Decimal("0.000001")) for key in OHLCV[:4]},
                "volume": int(candle["volume"]),
            }
    return [unique[stamp] for stamp in sorted(unique)]


@transaction.atomic
def _save_history(request: HistoryRequest, candles: list[dict]) -> int:
    """Publish a successful range only with its data; unchanged rows keep their revision."""
    Instrument.objects.select_for_update().only("pk").get(pk=request.instrument.pk)
    source = dict(symbol=request.instrument.sym_ticker, provider=settings.MARKET_DATA_PROVIDER,
                  timeframe=request.timeframe)
    existing = {
        row[0]: row[1:] for row in Candle.objects.filter(
            **source, time__gte=request.start, time__lt=request.end,
        ).values_list("time", *OHLCV, "provider_confirmed")
    }
    changed = [
        Candle(instrument=request.instrument, **source, provider_confirmed=True, **row)
        for row in candles if existing.get(row["time"]) != (*[row[key] for key in OHLCV], True)
    ]
    if changed:
        Candle.objects.bulk_create(
            changed, update_conflicts=True, unique_fields=["symbol", "provider", "timeframe", "time"],
            update_fields=[*OHLCV, "instrument", "provider_confirmed", "updated_at"], batch_size=2000,
        )
        transaction.on_commit(lambda: publish_revision(request.instrument.sym_ticker))

    now = django_timezone.now()
    coverage = HistoryCoverage.objects.filter(
        instrument=request.instrument, provider=settings.MARKET_DATA_PROVIDER, timeframe=request.timeframe,
    )
    coverage.filter(expires_at__lte=now).delete()
    # Only recent sessions expire. A request ending today must not make
    # months of older warmup expire with it and force another full download.
    # Empty responses are temporary negative cache entries, even for old dates.
    cutoff = request.calendar.session_open((now - RECENT_HISTORY).astimezone(request.calendar.zone).date())
    for start, end, expires in (
        (request.start, min(request.end, cutoff), None if candles else now + RECHECK_DELAY),
        (max(request.start, cutoff), request.end, now + RECHECK_DELAY),
    ):
        if start >= end:
            continue
        overlaps = coverage.filter(start__lte=end, end__gte=start, expires_at__isnull=expires is None)
        for left, right, previous_expiry in overlaps.values_list("start", "end", "expires_at"):
            start, end = min(start, left), max(end, right)
            if expires is not None:
                expires = min(expires, previous_expiry)
        overlaps.delete()
        HistoryCoverage.objects.create(
            instrument=request.instrument, provider=settings.MARKET_DATA_PROVIDER,
            timeframe=request.timeframe, start=start, end=end, expires_at=expires,
        )
    return len(changed)


def ensure_history(request: HistoryRequest, *, refresh: bool = False, max_requests: int = 0) -> HistoryResult:
    """Acquire missing source windows. A chart may bound the work to one request."""
    from .providers import provider

    request = completed_request(request)
    result = HistoryResult()
    if request.end <= request.start:
        return result
    result.missing = missing_history(request)
    pending = [_trading_range(request, request.start, request.end)] if refresh else result.missing
    if not any(pending):
        return result
    adapter, client = provider(), runtime_redis()
    lock_key = f"quantnest:history-lock:{settings.MARKET_DATA_PROVIDER}:{request.instrument.pk}:{request.timeframe}"
    try:
        while pending and (not max_requests or result.requests < max_requests):
            left, right = pending[-1]
            chunk_start = max(left, right - timedelta(days=adapter.history_window_days[request.timeframe]))
            if request.timeframe == "1D":
                # Split daily requests at a session opening, so the day straddling
                # a provider window is neither skipped nor requested twice.
                day = chunk_start.astimezone(request.calendar.zone).date()
                opening = request.calendar.session_open(day)
                if opening < chunk_start:
                    opening = request.calendar.session_open(day + timedelta(days=1))
                chunk_start = max(left, opening)
            chunk = replace(request, start=chunk_start, end=right)
            # Release after each bounded window. Overlapping callers recheck
            # coverage inside the same per-instrument/source lock.
            with client.lock(lock_key, timeout=180, blocking_timeout=3):
                gaps = [(chunk.start, chunk.end)] if refresh else missing_history(chunk)
                if gaps:
                    chunk = replace(chunk, start=gaps[0][0], end=gaps[-1][1])
                    candles = adapter.history(chunk)
                    prepared = _prepare_rows(chunk, candles)
                    result.changed += _save_history(chunk, prepared)
                    result.fetched += len(prepared)
                    result.requests += 1
            if refresh:
                pending.pop()
                if left < chunk_start:
                    pending.append((left, chunk_start))
            else:
                next_pending = missing_history(request)
                if next_pending == pending:
                    raise ProviderError("History preparation did not advance; retry shortly.")
                pending = next_pending
    except (ProviderError, LockError, RedisError) as exc:
        result.error = str(exc) if isinstance(exc, ProviderError) else "History preparation is busy or unavailable; retry shortly."
        logger.warning("History preparation failed symbol=%s source=%s: %s",
                       request.instrument.sym_ticker, request.timeframe, result.error)
    result.missing = pending if refresh else missing_history(request)
    return result


