"""One financial transition implementation for historical and running accounts.

Only an account owner calls these functions. Decisions on different instruments
remain parallel, but reservations and fills for one account are ordered here.
Nothing in this module queries a database, reads a quote, or contacts a broker.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, ROUND_HALF_UP

from common.costs import TradingCostCalculator
from common.enums import ExecutionSessionStatus, InstrumentType, OrderIntent, OrderStatus, OrderType, QuantityType, Side

from .types import ACTIVE_STATUSES, Account, ClosedTrade, Contract, EntryLot, Fill, Intent, MONEY, Order, Position, PositionView, Transition, UnitKey, ZERO


def margin(account: Account, contract: Contract, quantity: int, price: Decimal) -> Decimal:
    """Configured simulation collateral; a real broker remains its margin authority."""
    percentage = Decimal('100')
    if contract.instrument_type == InstrumentType.FUTURE:
        percentage = account.futures_margin_pct
    elif contract.instrument_type == InstrumentType.OPTION and quantity < 0:
        percentage = account.short_option_margin_pct
        if contract.strike_price is None or contract.strike_price <= ZERO:
            raise ValueError('Short option margin requires the contract strike price.')
        price = contract.strike_price
    return (contract.value(price, abs(quantity)) * percentage / 100).quantize(MONEY, rounding=ROUND_HALF_UP)


def available(account: Account, session_id: int) -> Decimal:
    used = sum((position.margin for position in account.positions.values()), ZERO)
    reserved = sum((order.reserved for order in account.working.values()), ZERO)
    free = account.balance - used - reserved - account.uncommitted_funds
    if account.live:
        free = min(free, account.broker_available - sum(account.broker_spending.values(), ZERO) - reserved)
    if session_id in account.allocations:
        session_used = sum((p.margin for key, p in account.positions.items() if key[1] == session_id), ZERO)
        session_reserved = sum((o.reserved for o in account.working.values() if o.unit[1] == session_id), ZERO)
        free = min(free, account.allocations[session_id] - session_used - session_reserved)
    return max(free, ZERO)


def position_view(account: Account, unit: UnitKey) -> PositionView:
    pending = any(order.unit == unit for order in account.working.values())
    position = account.positions.get(unit)
    if position is not None:
        return position.view(pending=pending)
    return PositionView(revision=account.position_revisions.get(unit, 0), pending=pending)


def size_order(sizing: dict, contract: Contract, price: Decimal, capital: Decimal) -> int:
    if price <= ZERO or not price.is_finite():
        return 0
    if sizing['sizing_method'] == QuantityType.FIXED:
        quantity = int(sizing['fixed_quantity'])
    elif sizing['sizing_method'] == QuantityType.CAPITAL_BASED:
        budget = max(capital, ZERO) * Decimal(str(sizing['capital_percentage'])) / 100
        quantity = int(budget / contract.value(price, 1))
    else:
        raise ValueError('Unsupported position sizing method.')
    return contract.units(quantity)


def order_transition(account: Account, order: Order, *, fill: Fill | None = None,
                trade: ClosedTrade | None = None) -> Transition:
    account.revision += 1
    account.index_order(order)
    # A queued database write must not change when a later observation mutates RAM.
    return Transition(f'{account.key[0]}:{account.key[1]}:{account.revision}', account.key,
        account.revision, deepcopy(order), deepcopy(account.positions.get(order.unit)),
        account.position_revisions.get(order.unit, 0), account.balance, account.realized,
        account.charges_paid, fill, trade, account.allocations.get(order.unit[1]))


def accept_intent(account: Account, intent: Intent, contract: Contract) -> Transition:
    """Admit exactly one action using current account facts, then reserve its funds."""
    if intent.account != account.key or intent.unit[2] != contract.instrument_id:
        raise ValueError('Intent does not belong to this account/instrument.')
    if intent.identity in account.orders:
        raise ValueError('This order intent has already been accepted.')
    if intent.side not in Side.values or intent.order_type not in OrderType.values:
        raise ValueError('Unsupported order side or type.')
    if not intent.reference_price.is_finite() or intent.reference_price <= ZERO:
        raise ValueError('An order requires a positive, finite market price.')
    if intent.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and intent.limit_price is None:
        raise ValueError('A limit price is required.')
    if intent.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT) and intent.trigger_price is None:
        raise ValueError('A trigger price is required.')
    view = position_view(account, intent.unit)
    session = intent.unit[1]
    if intent.position_revision != view.revision:
        raise ValueError('Position changed before this intent was accepted.')
    if not intent.manual:
        if intent.version != account.versions.get(session):
            raise ValueError('Strategy version changed before this intent was accepted.')
        if view.pending:
            raise ValueError('This instrument already has a pending strategy order.')
        if intent.intent == OrderIntent.ENTRY:
            if view.quantity or account.statuses.get(session) != ExecutionSessionStatus.RUNNING:
                raise ValueError('This session cannot open a new position.')
    quantity = intent.quantity
    closing = intent.intent == OrderIntent.EXIT or intent.reduce_only
    if closing:
        if not view.quantity or view.side == intent.side:
            raise ValueError('There is no owned position to reduce.')
        quantity = min(quantity, abs(view.quantity)) if intent.manual else abs(view.quantity)
    elif not quantity:
        quantity = size_order(account.sizing[intent.unit], contract, intent.reference_price, available(account, session))
    if account.live and not closing and (account.broker_observed_at is None or
            not 0 <= (intent.at - account.broker_observed_at).total_seconds() <= 90):
        raise ValueError('Wait for a fresh broker funds snapshot before opening a position.')
    contract.validate(quantity, (intent.limit_price, intent.trigger_price, intent.stop_loss, intent.take_profit), intent.at)
    signed = quantity if intent.side == Side.BUY else -quantity
    # Reserve only increased exposure. Ordinary manual sells can also close longs.
    old = account.positions.get(intent.unit)
    owned = old.quantity if old else 0
    already_closing = sum(o.remaining for o in account.working.values()
        if o.unit == intent.unit and o.side == intent.side)
    reducing = min(max(abs(owned) - already_closing, 0), quantity) if owned * signed < 0 else 0
    if closing and reducing < quantity:
        raise ValueError('Existing orders already reserve this position for closing.')
    reserved = margin(account, contract, signed // quantity * (quantity - reducing), intent.reference_price)
    if reserved > available(account, session):
        raise ValueError('Insufficient unreserved account or deployment capital.')
    order = Order(intent.identity, intent.unit, contract, intent.side, quantity, intent.at,
        intent.reason, intent=intent.intent, order_type=intent.order_type, price=intent.limit_price,
        trigger=intent.trigger_price, reduce_only=closing, reserved=reserved, version=intent.version,
        stop_loss=intent.stop_loss, take_profit=intent.take_profit, manual=intent.manual,
        charge_profile=deepcopy(account.profiles.get(session, {})), slippage_pct=account.slippage.get(session, ZERO),
        sequence=intent.sequence, generation=intent.generation, reference_price=intent.reference_price,
        status='UNKNOWN' if account.live else OrderStatus.PENDING)
    account.orders[order.identity] = order
    return order_transition(account, order)


def cancel_order(account: Account, identity: str, *, reason: str = '') -> Transition | None:
    order = account.orders[identity]
    if order.status not in ACTIVE_STATUSES:
        return None
    released = order.reserved
    order.status, order.reserved, order.error = OrderStatus.CANCELLED, ZERO, reason
    result = order_transition(account, order)
    hold_until_commit(account, result.revision, released)
    return result


def reject_order(account: Account, identity: str, reason: str) -> Transition:
    order = account.orders[identity]
    released = order.reserved
    order.status, order.reserved, order.error = OrderStatus.REJECTED, ZERO, reason
    result = order_transition(account, order)
    hold_until_commit(account, result.revision, released)
    return result


def hold_until_commit(account: Account, revision: int, amount: Decimal) -> None:
    """Released collateral and credits are spendable only after durable commit."""
    if amount > ZERO:
        account.pending_funds[revision] = account.pending_funds.get(revision, ZERO) + amount
        account.uncommitted_funds += amount


def _closing_costs(position: Position, order: Order, quantity: int, fill: Fill) -> tuple[dict, list[EntryLot]]:
    """Settle same-day lots first, then carried lots, using their original fee snapshots."""
    names = ('brokerage', 'stt', 'exchange_charges', 'sebi_fee', 'stamp_duty', 'gst', 'total')
    totals = {leg: dict.fromkeys(names, ZERO) for leg in ('entry_charges', 'exit_charges')}
    remaining, lots = quantity, []
    # Preserve the platform's same-day netting convention across all simulators.
    intraday = TradingCostCalculator.get_tax_classification(fill.at, fill.at)
    for lot in sorted(position.lots, key=lambda item: (
            TradingCostCalculator.get_tax_classification(item.at, fill.at) != intraday, item.at)):
        taken = min(lot.quantity, remaining)
        if taken:
            classification = TradingCostCalculator.get_tax_classification(lot.at, fill.at)
            side = Side.BUY if position.quantity > 0 else Side.SELL
            for leg, price, leg_side, profile in (
                ('entry_charges', lot.price, side, lot.charge_profile),
                ('exit_charges', fill.price, order.side, order.charge_profile),
            ):
                charges = TradingCostCalculator.calculate_charges(position.contract.value(price, taken),
                    position.contract.instrument_type, classification, leg_side, profile,
                    segment=position.contract.segment)
                # A partial close pays its share of the original entry-order flat fee.
                original = (lot.original_quantity or lot.quantity) if leg == 'entry_charges' else order.quantity
                full_brokerage = TradingCostCalculator.calculate_charges(position.contract.value(price, original),
                    position.contract.instrument_type, classification, leg_side, profile,
                    segment=position.contract.segment)['brokerage']
                before = lot.quantity if leg == 'entry_charges' else remaining
                amount = Decimal(str(full_brokerage))
                brokerage = ((amount * before / original).quantize(MONEY, rounding=ROUND_HALF_UP)
                    - (amount * (before - taken) / original).quantize(MONEY, rounding=ROUND_HALF_UP))
                charges['brokerage'] = brokerage
                # GST includes brokerage; recompute after proportional fee allocation.
                charges['gst'] = TradingCostCalculator.calculate_gst(brokerage,
                    Decimal(str(charges['exchange_charges'])), Decimal(str(charges['sebi_fee'])), profile) if 'gst_pct' in profile else ZERO
                charges['total'] = sum((Decimal(str(charges[name])) for name in names if name != 'total'), ZERO)
                for name in names:
                    totals[leg][name] += Decimal(str(charges[name]))
            remaining -= taken
        if lot.quantity > taken:
            lots.append(replace(lot, quantity=lot.quantity - taken))
    if remaining:
        raise ValueError('Entry fill history is incomplete; closing charges cannot be determined.')
    result = {leg: {key: float(value.quantize(MONEY, rounding=ROUND_HALF_UP)) for key, value in values.items()}
              for leg, values in totals.items()}
    result['total_charges'] = round(sum(values['total'] for values in result.values()), 2)
    return result, lots


def apply_fill(account: Account, fill: Fill) -> Transition:
    """Apply an incremental fill once; broker cumulative quantities are normalized first."""
    order = account.orders[fill.order_id]
    before_available = available(account, order.unit[1])
    if fill.quantity <= 0 or fill.quantity > order.remaining or not fill.price.is_finite() or fill.price < ZERO:
        raise ValueError('Invalid incremental fill.')
    if fill.at < order.eligible_at:
        raise ValueError('A fill cannot precede order eligibility.')
    previous = account.positions.get(order.unit)
    old_quantity = previous.quantity if previous else 0
    change = fill.quantity if order.side == Side.BUY else -fill.quantity
    if order.reduce_only and (not old_quantity or old_quantity * change >= 0 or fill.quantity > abs(old_quantity)):
        raise ValueError('Reduce-only fill would increase or reverse a position.')
    new_quantity = old_quantity + change
    closed = min(abs(old_quantity), fill.quantity) if old_quantity * change < 0 else 0
    opened = fill.quantity - closed
    average = previous.average if previous else fill.price
    if old_quantity * change > 0:
        average = (abs(old_quantity) * average + fill.quantity * fill.price) / abs(new_quantity)
    elif not old_quantity or old_quantity * new_quantity < 0:
        average = fill.price
    new_margin = margin(account, order.contract, new_quantity, average)
    old_margin = previous.margin if previous else ZERO
    if not account.live and opened and new_margin - old_margin > available(account, order.unit[1]) + order.reserved:
        return reject_order(account, order.identity, 'Insufficient capital at the actual fill price.')
    trade = None
    lots = list(previous.lots) if previous else []
    slippage = (order.contract.value(abs(fill.price - fill.reference_price), fill.quantity)
                if fill.reference_price is not None else ZERO)
    if closed:
        entry_slippage, left = ZERO, closed
        for lot in sorted(lots, key=lambda item: (
                TradingCostCalculator.get_tax_classification(item.at, fill.at) !=
                TradingCostCalculator.get_tax_classification(fill.at, fill.at), item.at)):
            taken = min(left, lot.quantity)
            entry_slippage += lot.slippage * taken
            left -= taken
        gross = order.contract.value(fill.price - previous.average, closed) * (1 if old_quantity > 0 else -1)
        if account.live:
            charges, remaining = {}, closed
            kept = []
            for lot in lots:
                taken = min(lot.quantity, remaining)
                remaining -= taken
                if lot.quantity > taken:
                    kept.append(replace(lot, quantity=lot.quantity - taken))
            lots = kept
        else:
            charges, lots = _closing_costs(previous, order, closed, fill)
        fees = Decimal(str(charges.get('total_charges', 0)))
        net = (gross - fees).quantize(MONEY, rounding=ROUND_HALF_UP)
        account.balance += net
        account.realized += net
        account.charges_paid += fees
        if order.unit[1] in account.allocations:
            account.allocations[order.unit[1]] += net
        trade = ClosedTrade(order.unit, order.contract, closed,
            Side.BUY if old_quantity > 0 else Side.SELL, previous.average, fill.price,
            previous.opened_at, fill.at, gross, net, charges, order.identity, order.reason,
            previous.mae, previous.mfe, entry_slippage + slippage * closed / fill.quantity)
    revision = account.position_revisions.get(order.unit, 0) + 1
    account.position_revisions[order.unit] = revision
    if new_quantity:
        reversal = old_quantity * new_quantity < 0
        if opened:
            lots.append(EntryLot(opened, fill.price, fill.at, order.identity, deepcopy(order.charge_profile), order.quantity, slippage / fill.quantity))
        position = Position(order.unit, order.contract, new_quantity, average,
            fill.at if previous is None or reversal else previous.opened_at,
            revision, new_margin, lots)
        if previous is not None and not reversal:
            position.stop_loss, position.take_profit = previous.stop_loss, previous.take_profit
            position.stop_distance, position.peak = previous.stop_distance, previous.peak
            position.mae, position.mfe = previous.mae, previous.mfe
        else:
            position.peak = float(fill.price)
        if opened:
            if order.stop_loss is not None:
                position.stop_loss = order.stop_loss
            if order.take_profit is not None:
                position.take_profit = order.take_profit
        account.positions[order.unit] = position
    else:
        account.positions.pop(order.unit, None)
    order.filled += fill.quantity
    order.filled_value += fill.price * fill.quantity
    order.status = OrderStatus.FILLED if not order.remaining else OrderStatus.PARTIAL_FILL
    order.reserved = order.reserved * order.remaining / (order.remaining + fill.quantity)
    transition = order_transition(account, order, fill=fill, trade=trade)
    if account.live and opened:
        debit = margin(account, order.contract, opened if order.side == Side.BUY else -opened, fill.price)
        account.broker_spending[transition.revision] = debit
        transition = replace(transition, broker_debit=debit)
    # Filled exposure is protected immediately, but new orders cannot spend an
    # uncommitted gain or released collateral until the writer acknowledges it.
    hold_until_commit(account, transition.revision, available(account, order.unit[1]) - before_available)
    return transition


def acknowledge(account: Account, revision: int) -> None:
    account.committed_revision = max(account.committed_revision, revision)
    for pending in tuple(account.pending_funds):
        if pending <= revision:
            account.uncommitted_funds -= account.pending_funds.pop(pending)
