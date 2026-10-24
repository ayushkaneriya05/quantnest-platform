"""Monotonic broker observations and cumulative fill accounting."""
from dataclasses import dataclass
from decimal import Decimal

from common.enums import OrderStatus

ZERO = Decimal("0")
UNKNOWN_STATUS = "UNKNOWN"  # Broker submission outcome is not yet confirmed.
TERMINAL = frozenset({OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED})
ACTIVE = frozenset({OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, UNKNOWN_STATUS})
STATUSES = TERMINAL | ACTIVE


@dataclass(frozen=True)
class OrderState:
    quantity: int
    filled: int = 0
    value: Decimal = ZERO
    status: str = UNKNOWN_STATUS


@dataclass(frozen=True)
class OrderTransition:
    state: OrderState
    fill_quantity: int = 0
    fill_price: Decimal = ZERO
    error: str = ""


def observe_order(previous: OrderState, *, status: str, filled: int, average: Decimal) -> OrderTransition:
    """Apply cumulative observations; repeats and older snapshots have no fill effect.

    An observation with quantity but no price cannot consume the fill cursor.
    A same-quantity cost correction requires verified fills, rather than silently
    rewriting already realised accounting.
    """
    if filled < 0 or filled > previous.quantity or not average.is_finite() or average < 0:
        return OrderTransition(previous, error="Invalid broker quantity or price")
    if filled < previous.filled:
        return OrderTransition(previous)
    value = average * filled
    delta = filled - previous.filled
    if not delta and average <= 0:
        value = previous.value
    if delta and (average <= 0 or value <= previous.value):
        return OrderTransition(previous, error="Additional fill has no valid execution value")
    if not delta and filled and value != previous.value:
        return OrderTransition(previous, error="Cumulative cost correction requires verified broker fills")
    if status not in STATUSES:
        status = UNKNOWN_STATUS
    if status == OrderStatus.FILLED and filled != previous.quantity:
        return OrderTransition(previous, error="Completed broker order has incomplete cumulative fill quantity")
    if filled == previous.quantity and filled:
        status = OrderStatus.FILLED
    elif previous.status in TERMINAL:
        status = previous.status
    elif filled and status in {OrderStatus.PENDING, OrderStatus.PLACED, UNKNOWN_STATUS}:
        status = OrderStatus.PARTIAL_FILL
    elif previous.status == OrderStatus.PLACED and status in {OrderStatus.PENDING, UNKNOWN_STATUS}:
        status = OrderStatus.PLACED
    return OrderTransition(
        OrderState(previous.quantity, filled, value if filled else ZERO, status),
        delta,
        (value - previous.value) / delta if delta else ZERO,
    )
