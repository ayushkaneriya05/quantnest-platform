"""Shared display/valuation prices. Execution uses the local observation buffer."""
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import TypedDict

from django.conf import settings
from django.core.cache import caches

from .contracts import SOURCE_TIMEFRAMES, normalize_symbol

cache = caches["marketdata"]


class QuoteSnapshot(TypedDict):
    symbol: str
    price: float | None
    timestamp: str | None
    updated_at: str | None
    source: str
    available: bool
    change_percent: float | None


def publish_quote(symbol: str, quote: dict) -> QuoteSnapshot:
    """Only the feed publishes observations; HTTP quotes have a separate cache."""
    payload = {**quote, "symbol": symbol, "source": "observed", "available": True}
    cache.set(f"marketdata:quote:{settings.MARKET_DATA_PROVIDER}:{symbol}", payload, 86400)
    return payload


def _stored_quote(symbol: str) -> dict:
    from .calendar import MarketSessionCalendar
    from .models import Candle
    now = datetime.now(timezone.utc)
    candles = Candle.objects.filter(symbol=symbol, provider=settings.MARKET_DATA_PROVIDER,
                                    provider_confirmed=True, time__lte=now)
    candidates = []
    for source in SOURCE_TIMEFRAMES:
        series = candles.filter(timeframe=source)
        row = series.filter(time__gte=now - timedelta(days=7)).order_by("-time").first()
        if row is not None:
            candidates.append(row)
    if not candidates:
        from .models import HistoryCoverage
        # No acquired series means there is no older confirmed price to find.
        if not HistoryCoverage.objects.filter(
            instrument__sym_ticker=symbol, provider=settings.MARKET_DATA_PROVIDER,
        ).exists():
            return {}
        # One older-price fallback, instead of an unbounded scan for each
        # missing source family (e.g. no daily series for a minute-only symbol).
        row = candles.filter(timeframe__in=SOURCE_TIMEFRAMES).order_by("-time").first()
        if row is None:
            return {}
        candidates.append(row)
    calendar = MarketSessionCalendar.for_symbol(symbol)
    first = min(row.time for row in candidates).astimezone(calendar.zone).date()
    calendar.load_holidays(first - timedelta(days=7), now.astimezone(calendar.zone).date() + timedelta(days=1))
    newest = max(candidates, key=lambda row: row.time)
    opening, closing = calendar.session_bounds(newest.time)
    if not any(row.timeframe == "1D" and row.time >= opening for row in candidates):
        daily = candles.filter(timeframe="1D", time__gte=opening, time__lt=closing).order_by("-time").first()
        if daily is not None:
            candidates.append(daily)
    # A confirmed daily close is newer than the opening of the last minute.
    # Compare when values became available, preferring the daily close on ties.
    latest = max(candidates, key=lambda row: (calendar.candle_close(row.time, row.timeframe), row.timeframe == "1D"))
    opening = calendar.session_bounds(latest.time)[0]
    # A missing recent daily series must not scan years of compressed history
    # merely to display a change percentage. Leave it unknown when absent.
    previous = candles.filter(timeframe="1D", time__gte=opening - timedelta(days=31),
                              time__lt=opening).order_by("-time").first()
    price = float(latest.close)
    return {
        "symbol": symbol, "price": price, "source": "history", "available": True,
        "timestamp": calendar.candle_close(latest.time, latest.timeframe).isoformat(),
        "updated_at": latest.updated_at.isoformat(),
        "change_percent": (price / float(previous.close) - 1) * 100 if previous else None,
    }


def read_quote(sym_ticker: str) -> QuoteSnapshot:
    symbol = normalize_symbol(sym_ticker)
    source = settings.MARKET_DATA_PROVIDER
    observed = cache.get(f"marketdata:quote:{source}:{symbol}")
    provider_quote = cache.get(f"marketdata:rest-quote:{source}:{symbol}")
    observations = [value for value in (observed, provider_quote) if value]
    if observations:
        return max(observations, key=lambda value: datetime.fromisoformat(value['timestamp']))
    # History is cached by data revision; opening many positions does not repeat
    # the same database lookups. A later provider correction changes this key.
    from .history import data_revision
    key = f"marketdata:last-close:{source}:{symbol}:{data_revision(symbol)}"
    stored = cache.get(key)
    if stored is None:
        stored = _stored_quote(symbol)
        cache.set(key, stored, 30)
    if stored:
        return stored
    return {"symbol": symbol, "price": None, "timestamp": None, "updated_at": None,
            "source": "unavailable", "available": False, "change_percent": None}


def refresh_quote(sym_ticker: str) -> QuoteSnapshot:
    """Explicit, bounded HTTP refresh used by the quote endpoint, never execution."""
    from .providers import provider
    symbol = normalize_symbol(sym_ticker)
    key = f"marketdata:rest-quote:{settings.MARKET_DATA_PROVIDER}:{symbol}"
    if not cache.add(f"{key}:loading", True, 5):
        return read_quote(symbol)
    # Keep the short acquisition marker through its TTL, including failed calls.
    # Concurrent browser requests reuse the observation or last known close.
    value = provider().quote(symbol)
    if value and isfinite(float(value["price"])) and value["price"] > 0:
        cache.set(key, {**value, "symbol": symbol, "available": True}, 60)
    return read_quote(symbol)
