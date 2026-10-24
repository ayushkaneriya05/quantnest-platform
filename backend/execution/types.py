"""Explicit values passed between evaluation, account ownership and persistence.

Convert Django/provider objects at the boundary. The kernel accepts these values,
never a mixture of model instances, dictionaries and provider payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN

from common.enums import ExecutionMode, InstrumentType, OrderIntent, OrderStatus, OrderType, ProductType, Side
from execution.order_reports import ACTIVE as ACTIVE_STATUSES

ZERO = Decimal('0')
ONE = Decimal('1')
MONEY = Decimal('0.01')
PRICE = Decimal('0.00000001')
UnitKey = tuple[str, int, int]  # mode, session, instrument
AccountKey = tuple[str, int]  # mode, paper/terminal account or broker credential


@dataclass(frozen=True, slots=True)
class Contract:
    instrument_id: int
    symbol: str
    name: str
    instrument_type: str
    exchange: str
    segment: int
    tick_size: Decimal
    lot_size: int
    multiplier: Decimal
    expiry: date | None = None
    quantity_freeze: int = 0
    lower_band: Decimal | None = None
    upper_band: Decimal | None = None
    tradeable: bool = True
    strike_price: Decimal | None = None

    def __post_init__(self) -> None:
        if (self.lot_size < 1 or not self.tick_size.is_finite() or self.tick_size <= ZERO
                or not self.multiplier.is_finite() or self.multiplier <= ZERO):
            raise ValueError('Contract lot size, tick size and multiplier must be positive.')

    @property
    def product(self) -> str:
        return (ProductType.CNC if self.instrument_type in
                (InstrumentType.STOCK, InstrumentType.ETF, InstrumentType.BOND) else ProductType.MARGIN)

    def value(self, price: Decimal, quantity: int) -> Decimal:
        return price * quantity * self.multiplier

    def units(self, requested: int) -> int:
        return max(requested, 0) // self.lot_size * self.lot_size

    def price(self, value: Decimal) -> Decimal:
        return (value / self.tick_size).to_integral_value(rounding=ROUND_DOWN) * self.tick_size

    def validate(self, quantity: int, prices: tuple[Decimal | None, ...], at: datetime) -> None:
        if not self.tradeable or self.instrument_type in (InstrumentType.INDEX, InstrumentType.MF):
            raise ValueError('This instrument is available for analysis only.')
        if self.expiry is not None and self.expiry < at.date():
            raise ValueError('This contract has expired.')
        if quantity <= 0 or quantity != self.units(quantity):
            raise ValueError(f'Quantity must be a positive multiple of {self.lot_size}.')
        if self.quantity_freeze and quantity > self.quantity_freeze:
            raise ValueError(f'Maximum quantity per order is {self.quantity_freeze}.')
        for value in prices:
            if value is None:
                continue
            if not value.is_finite() or value <= ZERO or self.price(value) != value:
                raise ValueError(f'Price must be a positive multiple of {self.tick_size}.')
            if self.lower_band is not None and value < self.lower_band:
                raise ValueError('Price is below the contract lower band.')
            if self.upper_band is not None and value > self.upper_band:
                raise ValueError('Price is above the contract upper band.')


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    sequence: int
    event_time: datetime
    received_at: float
    price: float
    volume: float = 0.0
    generation: int = 0
    closed_at: datetime | None = None

    @property
    def evaluated_at(self) -> datetime:
        return self.closed_at or self.event_time


@dataclass(frozen=True, slots=True)
class Candle:
    opened_at: datetime
    closed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class PositionView:
    """Read-only position input for one evaluator; only the owner can change quantity."""
    revision: int = 0
    quantity: int = 0  # signed: positive long, negative short
    average: Decimal = ZERO
    opened_at: datetime | None = None
    stop_distance: float = 0.0
    pending: bool = False

    @property
    def side(self) -> str:
        return Side.BUY if self.quantity >= 0 else Side.SELL


@dataclass(frozen=True, slots=True)
class Intent:
    identity: str
    account: AccountKey
    unit: UnitKey
    version: int
    position_revision: int
    sequence: int
    at: datetime
    side: str
    reason: str
    reference_price: Decimal
    intent: str = OrderIntent.ENTRY
    quantity: int = 0  # zero means the owner applies the admitted sizing rule
    order_type: str = OrderType.MARKET
    limit_price: Decimal | None = None
    trigger_price: Decimal | None = None
    reduce_only: bool = False
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    manual: bool = False
    generation: int = 0
    observed_at: datetime | None = None


@dataclass(slots=True)
class Order:
    identity: str
    unit: UnitKey
    contract: Contract
    side: str
    quantity: int
    eligible_at: datetime
    reason: str
    intent: str = OrderIntent.ENTRY
    order_type: str = OrderType.MARKET
    price: Decimal | None = None
    trigger: Decimal | None = None
    reduce_only: bool = False
    activated_at: datetime | None = None
    filled: int = 0
    filled_value: Decimal = ZERO
    status: str = OrderStatus.PENDING
    reserved: Decimal = ZERO
    version: int = 0
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    charge_profile: dict = field(default_factory=dict)
    slippage_pct: Decimal = ZERO
    persisted: bool = False
    broker_id: str = ''
    broker_ordered_at: datetime | None = None
    broker_updated_at: datetime | None = None
    exchange_order_id: str = ''
    error: str = ''
    manual: bool = False
    sequence: int = 0
    generation: int = 0
    cancel_requested: bool = False
    reference_price: Decimal = ZERO

    @property
    def remaining(self) -> int:
        return self.quantity - self.filled


@dataclass(frozen=True, slots=True)
class EntryLot:
    quantity: int
    price: Decimal
    at: datetime
    order_id: str
    charge_profile: dict
    original_quantity: int = 0
    slippage: Decimal = ZERO


@dataclass(slots=True)
class Position:
    unit: UnitKey
    contract: Contract
    quantity: int
    average: Decimal
    opened_at: datetime
    revision: int = 0
    margin: Decimal = ZERO
    lots: list[EntryLot] = field(default_factory=list)
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    stop_distance: float = 0.0
    peak: float = 0.0
    mae: Decimal = ZERO
    mfe: Decimal = ZERO

    def view(self, *, pending: bool) -> PositionView:
        return PositionView(self.revision, self.quantity, self.average,
                            self.opened_at, self.stop_distance, pending)


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    unit: UnitKey
    contract: Contract
    quantity: int
    side: str
    entry_price: Decimal
    exit_price: Decimal
    entry_time: datetime
    exit_time: datetime
    gross: Decimal
    net: Decimal
    charges: dict
    exit_order: str
    reason: str
    mae: Decimal = ZERO
    mfe: Decimal = ZERO
    slippage: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    quantity: int
    price: Decimal
    at: datetime
    reference_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Transition:
    """Exact financial effects; the writer persists these without trading calculations."""
    identity: str
    account: AccountKey
    revision: int
    order: Order
    position: Position | None
    position_revision: int
    balance: Decimal
    realized: Decimal
    charges_paid: Decimal
    fill: Fill | None = None
    trade: ClosedTrade | None = None
    allocation: Decimal | None = None
    broker_debit: Decimal = ZERO


@dataclass(slots=True)
class Account:
    key: AccountKey
    balance: Decimal  # settled equity excluding unrealized price changes
    revision: int = 0
    committed_revision: int = 0
    realized: Decimal = ZERO
    charges_paid: Decimal = ZERO
    positions: dict[UnitKey, Position] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    working: dict[str, Order] = field(default_factory=dict, init=False, repr=False, compare=False)
    position_revisions: dict[UnitKey, int] = field(default_factory=dict)
    allocations: dict[int, Decimal] = field(default_factory=dict)
    allocation_principal: dict[int, Decimal] = field(default_factory=dict)
    versions: dict[int, int] = field(default_factory=dict)
    statuses: dict[int, str] = field(default_factory=dict)
    sizing: dict[UnitKey, dict] = field(default_factory=dict)
    profiles: dict[int, dict] = field(default_factory=dict)
    slippage: dict[int, Decimal] = field(default_factory=dict)
    futures_margin_pct: Decimal = Decimal('100')
    short_option_margin_pct: Decimal = Decimal('100')
    uncommitted_funds: Decimal = ZERO
    pending_funds: dict[int, Decimal] = field(default_factory=dict)
    close_on_stop: dict[int, bool] = field(default_factory=dict)
    broker_available: Decimal = ZERO
    broker_observed_at: datetime | None = None
    broker_spending: dict[int, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        # Derived once at recovery, never serialized as another source of truth.
        self.working = {key: order for key, order in self.orders.items() if order.status in ACTIVE_STATUSES}

    def index_order(self, order: Order) -> None:
        if order.status in ACTIVE_STATUSES:
            self.working[order.identity] = order
        else:
            self.working.pop(order.identity, None)

    @property
    def live(self) -> bool:
        return self.key[0] == ExecutionMode.LIVE
