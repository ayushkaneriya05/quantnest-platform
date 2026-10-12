"""Provider-neutral identities, market events and contract specifications."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Protocol


@dataclass(frozen=True)
class Contract:
    instrument_id: int
    venue: str
    asset_type: str
    currency: str
    tick_size: Decimal
    lot_size: int = 1
    multiplier: Decimal = Decimal("1")

    def quantity(self, units):
        if self.lot_size <= 0:
            raise ValueError("Contract lot size must be positive")
        return max(int(units) // self.lot_size * self.lot_size, 0)

    def price(self, value):
        tick_size = Decimal(str(self.tick_size))
        if not tick_size.is_finite() or tick_size <= 0:
            raise ValueError("Contract tick size must be positive")
        value = Decimal(str(value))
        if not value.is_finite() or value <= 0:
            raise ValueError("Price must be finite and positive")
        return (value / tick_size).to_integral_value(rounding=ROUND_DOWN) * tick_size

    def notional(self, price, quantity):
        return Decimal(str(price)) * int(quantity) * Decimal(str(self.multiplier))


@dataclass(frozen=True)
class MarketEvent:
    instrument_id: int
    symbol: str
    source: str
    event_time: float
    received_time: float
    price: float
    volume: float = 0
    sequence: int | None = None
    bid: float | None = None
    ask: float | None = None


@dataclass(frozen=True)
class DataCapabilities:
    trades: bool = False
    quotes: bool = True
    depth: bool = False
    historical: bool = True
    sequence: bool = False


class MarketDataAdapter(Protocol):
    name: str
    capabilities: DataCapabilities

    def quote(self, symbol): ...

    def live_client(self): ...

    def history(self, symbol, timeframe, start, end): ...
