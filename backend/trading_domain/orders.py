"""Monotonic broker observations and cumulative fill accounting."""
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")
TERMINAL = frozenset({"FILLED", "REJECTED", "CANCELLED", "EXPIRED"})
STATUSES = TERMINAL | {"PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"}


@dataclass(frozen=True)
class OrderState:
    quantity: int
    filled: int = 0
    value: Decimal = ZERO
    status: str = "UNKNOWN"


@dataclass(frozen=True)
class OrderTransition:
    state: OrderState
    fill_quantity: int = 0
    fill_price: Decimal = ZERO
    error: str = ""


def observe_order(previous, *, status, filled, average):
    """Apply cumulative observations; repeats and older snapshots have no fill effect.

    An observation with quantity but no price cannot consume the fill cursor.
    A same-quantity cost correction requires verified fills, rather than silently
    rewriting already realised accounting.
    """
    filled = int(filled or 0)
    average = Decimal(str(average or 0))
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
    status = str(status or "UNKNOWN").upper()
    if status not in STATUSES:
        status = "UNKNOWN"
    if status == "FILLED" and filled != previous.quantity:
        return OrderTransition(previous, error="Completed broker order has incomplete cumulative fill quantity")
    if filled == previous.quantity and filled:
        status = "FILLED"
    elif previous.status in TERMINAL:
        status = previous.status
    elif filled and status in {"PENDING", "PLACED", "UNKNOWN"}:
        status = "PARTIAL_FILL"
    elif previous.status == "PLACED" and status in {"PENDING", "UNKNOWN"}:
        status = "PLACED"
    return OrderTransition(
        OrderState(previous.quantity, filled, value if filled else ZERO, status),
        delta,
        (value - previous.value) / delta if delta else ZERO,
    )
