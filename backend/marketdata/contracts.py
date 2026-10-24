"""Provider-independent data contracts. All internal ranges are UTC [start, end)."""
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING

from common.enums import ChartTimeframe

if TYPE_CHECKING:
    from instruments.models import Instrument
    from .calendar import MarketSessionCalendar

SOURCE_TIMEFRAMES = (ChartTimeframe.M1, ChartTimeframe.D1)
OHLCV = ("open", "high", "low", "close", "volume")


def normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.count(":") != 1 or not all(value.split(":")):
        raise ValueError("Use the instrument's exchange-qualified sym_ticker.")
    return value


def interval_minutes(interval: str):
    if interval not in ChartTimeframe.values:
        raise ValueError(f"Unsupported candle interval '{interval}'.")
    if interval in (ChartTimeframe.D1, ChartTimeframe.W1, ChartTimeframe.MN1):
        return None
    return int(interval[:-1]) * (60 if interval.endswith("H") else 1)


def source_timeframe(interval: str) -> str:
    return ChartTimeframe.M1 if interval_minutes(interval) else ChartTimeframe.D1


def valid_candle(row: dict) -> bool:
    opening, high, low, close, volume = (float(row[key]) for key in OHLCV)
    return (all(isfinite(value) for value in (opening, high, low, close, volume))
            and min(opening, high, low, close) > 0 and volume >= 0
            and low <= min(opening, close) <= max(opening, close) <= high)


@dataclass(frozen=True)
class HistoryRequest:
    instrument: "Instrument"
    timeframe: str
    start: datetime
    end: datetime
    calendar: "MarketSessionCalendar"

    def __post_init__(self):
        if self.timeframe not in SOURCE_TIMEFRAMES:
            raise ValueError("History ingestion accepts one-minute or daily sources.")
        if self.start.utcoffset() is None or self.end.utcoffset() is None:
            raise ValueError("History boundaries must include a timezone.")
        if self.end < self.start:
            raise ValueError("History end must be on or after its start.")


@dataclass
class HistoryResult:
    fetched: int = 0
    changed: int = 0
    requests: int = 0
    missing: list[tuple[datetime, datetime]] = field(default_factory=list)
    error: str = ""

    @property
    def complete(self) -> bool:
        return not self.missing and not self.error


@dataclass(frozen=True)
class CandleRequest:
    instrument: "Instrument"
    timeframe: str
    start: datetime
    end: datetime
    calendar: "MarketSessionCalendar"
    limit: int = 0
    include_open: bool = False

    def __post_init__(self):
        interval_minutes(self.timeframe)
        if self.start.utcoffset() is None or self.end.utcoffset() is None:
            raise ValueError("Candle boundaries must include a timezone.")
        if self.end < self.start or self.limit < 0:
            raise ValueError("Invalid candle range or limit.")


class ProviderError(Exception):
    """A failed acquisition is never interpreted as a successful empty response."""
