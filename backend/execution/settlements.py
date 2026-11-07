"""Sourced derivative accounting events, separate from orders and market ticks.

The controller supplies immutable facts. This module does no I/O and never
changes a trade's original entry price. A daily payment follows the remaining
units until they close, preventing the exit from paying the same P&L twice.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from common.enums import InstrumentType, OptionType, SettlementKind, Side
from .ledger import available, hold_until_commit
from .types import Account, ClosedTrade, MONEY, UnitKey, ZERO


@dataclass(frozen=True, slots=True)
class SettlementPrice:
    identity: int
    instrument_id: int
    kind: str
    value: Decimal  # Future price; underlying settlement value for an option.
    effective_at: datetime
    available_at: datetime
    source: str
    cash_settled: bool = False
    fee_per_unit: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SettlementResult:
    identity: str
    price_id: int
    unit: UnitKey
    quantity: int
    opened_at: datetime
    effective_at: datetime
    gross: Decimal  # Payment since the preceding settlement, before fees.
    fees: Decimal
    cash_change: Decimal
    trade: ClosedTrade | None = None


def apply_settlement(account: Account, unit: UnitKey, price: SettlementPrice, *,
                     now: datetime, quantity: int, opened_at: datetime) -> SettlementResult | None:
    """Apply exactly once to the specified position cycle, or reject unchanged.

    Delayed reports after a later fill need reconciliation: current quantity
    cannot be used as a substitute for quantity owned at the historical cutoff.
    Live accounts deliberately require a future broker-report adapter rather
    than treating a market-wide price as an account cash/assignment report.
    """
    identity = f'{price.identity}:{unit[0]}:{unit[1]}:{unit[2]}:{unit[3]}:{opened_at.isoformat()}'
    if identity in account.settlements:
        return None
    if account.live:
        raise ValueError('Live settlement requires a qualified account-specific broker/clearing report.')
    if (now.tzinfo is None or price.effective_at.tzinfo is None or price.available_at.tzinfo is None
            or opened_at.tzinfo is None or not price.source.strip()
            or price.available_at < price.effective_at or now < price.available_at):
        raise ValueError('Settlement needs a sourced, timezone-aware observation available at this clock time.')
    if not price.value.is_finite() or price.value < ZERO:
        raise ValueError('Settlement value must be finite and nonnegative.')
    position = account.positions.get(unit)
    if (position is None or position.contract.instrument_id != price.instrument_id
            or position.quantity != quantity or position.opened_at != opened_at):
        raise ValueError('The settlement does not match the currently owned position cycle and quantity.')
    contract = position.contract
    if price.kind == SettlementKind.FINAL and any(order.unit == unit for order in account.working.values()):
        raise ValueError('Reconcile working orders before applying settlement.')
    if (position.last_fill_at or position.opened_at) > price.effective_at:
        raise ValueError('A later fill exists. Reconcile the historical settlement instead of marking current quantity.')
    if position.settled_at is not None and price.effective_at <= position.settled_at:
        raise ValueError('Settlement cutoff must follow the last applied settlement.')
    if price.kind == SettlementKind.DAILY:
        if contract.instrument_type != InstrumentType.FUTURE or price.value <= ZERO:
            raise ValueError('Daily MTM requires a positive official futures settlement price.')
        value, fees = price.value, ZERO
    elif price.kind == SettlementKind.FINAL:
        if not price.cash_settled:
            raise ValueError('Physical delivery and devolvement need delivery records, not cash settlement.')
        if contract.instrument_type == InstrumentType.OPTION:
            if (contract.strike_price is None or not contract.strike_price.is_finite()
                    or contract.strike_price <= ZERO or contract.option_type not in OptionType.values):
                raise ValueError('Final option settlement requires qualified strike and option right.')
            difference = price.value - contract.strike_price
            value = max(difference if contract.option_type == OptionType.CE else -difference, ZERO)
        elif contract.instrument_type == InstrumentType.FUTURE and price.value > ZERO:
            value = price.value
        else:
            raise ValueError('Final settlement requires a qualified future or option.')
        if price.fee_per_unit is None or not price.fee_per_unit.is_finite() or price.fee_per_unit < ZERO:
            raise ValueError('Supply explicit settlement fees; ordinary order brokerage is not an exercise fee.')
        fees = (price.fee_per_unit * abs(quantity)).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        raise ValueError('Unsupported settlement kind.')

    # All rejection paths precede mutation. Losses are posted even if they make
    # free collateral zero; insufficient funds cannot erase economic reality.
    before_available = available(account, unit[1])
    gross = position.unsettled_pnl(value).quantize(MONEY, rounding=ROUND_HALF_UP)
    cash_change = gross - fees
    trade = None
    if price.kind == SettlementKind.FINAL:
        lifetime = contract.value(value - position.average, quantity)
        trade = ClosedTrade(unit, contract, abs(quantity), Side.BUY if quantity > 0 else Side.SELL,
            position.average, value, position.opened_at, price.effective_at, lifetime,
            lifetime - fees, {'total_charges': str(fees), 'settlement_charges': str(fees)},
            '', 'OFFICIAL_CASH_SETTLEMENT', position.mae, position.mfe, settled_pnl=position.settled_pnl)
        del account.positions[unit]
    else:
        position.settled_pnl += gross
        position.settled_at = price.effective_at
        position.revision += 1
    account.position_revisions[unit] = account.position_revisions.get(unit, 0) + 1
    account.balance += cash_change
    account.realized += cash_change
    account.charges_paid += fees
    if unit[1] in account.allocations:
        account.allocations[unit[1]] += cash_change
    account.revision += 1
    account.settlements[identity] = account.revision
    hold_until_commit(account, account.revision, available(account, unit[1]) - before_available)
    return SettlementResult(identity, price.identity, unit, quantity, opened_at,
                            price.effective_at, gross, fees, cash_change, deepcopy(trade))
