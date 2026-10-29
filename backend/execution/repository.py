"""Database admission, recovery and exact financial writes for execution.

The worker never calls this module. A background writer commits the checkpoint
and the application's existing order, position and trade records together.
"""
from copy import deepcopy
from decimal import Decimal
import json

from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from common.enums import ExecutionMode, OrderStatus, Side, TerminalOrderStatus, TerminalOrderType

from .models import AccountCheckpoint, Command
from .snapshots import decode, encode
from .types import Account, Transition, ZERO

TERMINAL_STATUS = {OrderStatus.PENDING: TerminalOrderStatus.OPEN, OrderStatus.PLACED: TerminalOrderStatus.OPEN,
    OrderStatus.PARTIAL_FILL: TerminalOrderStatus.OPEN, OrderStatus.FILLED: TerminalOrderStatus.COMPLETE,
    OrderStatus.CANCELLED: TerminalOrderStatus.CANCELLED, OrderStatus.REJECTED: TerminalOrderStatus.REJECTED,
    OrderStatus.EXPIRED: TerminalOrderStatus.CANCELLED}


def enqueue(mode: str, account_id: int, kind: str, payload: dict, *, request_id=None) -> Command:
    """Call inside the CRUD transaction, after permissions and allowance admission."""
    values = {'request_id': request_id} if request_id is not None else {}
    return Command.objects.create(mode=mode, account_id=account_id, kind=kind,
        payload=json.loads(json.dumps(payload, cls=DjangoJSONEncoder)), **values)


@transaction.atomic
def reject_command(command, error):
    """Persist failure and release funds reserved by admission, exactly once."""
    from common.enums import ExecutionCommandType, TransactionType
    command = Command.objects.select_for_update().get(pk=command.pk)
    if command.applied_at is not None:
        return
    command.error, command.applied_at = error, timezone.now()
    command.save(update_fields=['error', 'applied_at'])
    if command.mode == ExecutionMode.TERMINAL and command.kind in (ExecutionCommandType.ORDER, ExecutionCommandType.SETTLE):
        from trading.models import Order
        from trading.signals import order_status_changed
        order = Order.objects.filter(request_id=command.request_id).first()
        if order is not None:
            order.status, order.rejection_reason, order.reserved_cash = TerminalOrderStatus.REJECTED, error, ZERO
            order.save(update_fields=['status', 'rejection_reason', 'reserved_cash'])
            order_status_changed.send(sender=Order, order=order)
    elif command.kind not in (ExecutionCommandType.BROKER, ExecutionCommandType.FUNDS):
        # Admission is asynchronous: report owner rejection to the user instead
        # of leaving a successful HTTP response as the only visible outcome.
        from notifications.services import NotificationService
        from common.enums import NotificationType
        from trading.models import Account as TerminalAccount
        from paper_trading.models import PaperAccount
        from brokers.models import BrokerCredential
        model = {ExecutionMode.TERMINAL: TerminalAccount, ExecutionMode.PAPER: PaperAccount,
                 ExecutionMode.LIVE: BrokerCredential}[command.mode]
        user_id = model.objects.filter(pk=command.account_id).values_list('user_id', flat=True).first()
        if user_id is not None:
            transaction.on_commit(lambda: NotificationService.notify(user_id=user_id,
                title='Execution change could not be applied', message=error,
                type=NotificationType.WARNING,
                data={'module': command.mode, 'command_id': str(command.pk), 'action': command.kind},
                dedupe_key=f'execution-command:{command.pk}:rejected'), robust=True)
    if command.kind == ExecutionCommandType.BALANCE and command.payload.get('wallet_debited'):
        from paper_trading.models import Portfolio, FundTransaction
        wallet = Portfolio.objects.select_for_update().get(pk=command.payload['portfolio_id'])
        before, delta = wallet.current_capital, Decimal(command.payload['delta'])
        wallet.current_capital += delta
        wallet.save(update_fields=['current_capital', 'updated_at'])
        FundTransaction.objects.create(portfolio=wallet, transaction_type=TransactionType.ADJUSTMENT,
            amount=delta, balance_before=before, balance_after=wallet.current_capital,
            notes=f'Capital change was not applied: {error}'[:255])


@transaction.atomic
def initialize_account(account: Account) -> Account:
    account.__post_init__()
    row, created = AccountCheckpoint.objects.get_or_create(mode=account.key[0], account_id=account.key[1],
        defaults={'revision': account.revision, 'state': encode(account)})
    return account if created else decode(row.state)


def restore_account(key) -> Account | None:
    row = AccountCheckpoint.objects.filter(mode=key[0], account_id=key[1]).first()
    return decode(row.state) if row else None


def persist_evaluations(messages):
    from .models import EvaluationCheckpoint
    # Recovery fences these records by the committed position revision/version.
    # A newer evaluator checkpoint cannot invent an uncommitted position.
    EvaluationCheckpoint.objects.bulk_create([EvaluationCheckpoint(mode=message.unit[0],
        session_id=message.unit[1], instrument_id=message.unit[2], version_id=message.version,
        position_revision=message.position_revision, state=encode(message.state)) for message in messages],
        update_conflicts=True, unique_fields=['mode', 'session_id', 'instrument_id'],
        update_fields=['version_id', 'position_revision', 'state', 'updated_at'], batch_size=500)


def _paper(result: Transition, state: Account):
    from paper_trading.models import PaperAccount, PaperOrder, PaperPosition, PaperTrade, PaperTradingSession
    session = PaperTradingSession.objects.get(pk=result.order.unit[1])
    order, position, trade = result.order, result.position, result.trade
    defaults = {
        'account_id': state.key[1], 'strategy_id': session.strategy_id,
        'instrument_id': order.contract.instrument_id, 'reason': order.reason[:255],
        'order_type': order.order_type, 'product_type': order.contract.product, 'side': order.side,
        'quantity': order.quantity, 'price': order.price or order.reference_price, 'trigger_price': order.trigger,
        'filled_quantity': order.filled, 'avg_fill_price': order.filled_value/order.filled if order.filled else None,
        'slippage_pct_applied': order.slippage_pct, 'status': order.status, 'rejection_reason': order.error,
        'order_tag': order.intent}
    if result.fill is not None:
        defaults['executed_at'] = result.fill.at
    record, _ = PaperOrder.objects.update_or_create(request_id=order.identity, defaults=defaults)
    owned = PaperPosition.objects.filter(account_id=state.key[1], instrument_id=order.contract.instrument_id)
    if result.fill is not None:
        if position is None:
            owned.delete()
        else:
            record_position, _ = PaperPosition.objects.update_or_create(account_id=state.key[1],
                instrument_id=order.contract.instrument_id, defaults={'strategy_id': session.strategy_id,
                'side': Side.BUY if position.quantity > 0 else Side.SELL, 'quantity': abs(position.quantity),
                'avg_price': position.average, 'current_price': result.fill.price,
                'margin_blocked': position.margin, 'unrealized_pnl': ZERO})
            # auto_now_add must not replace the actual execution timestamp.
            owned.filter(pk=record_position.pk).update(opened_at=position.opened_at)
    if trade is not None:
        fees = Decimal(str(trade.charges.get('total_charges', 0)))
        brokerage = sum((Decimal(str(trade.charges.get(leg, {}).get('brokerage', 0)))
                         for leg in ('entry_charges', 'exit_charges')), ZERO)
        PaperTrade.objects.create(account_id=state.key[1], strategy_id=session.strategy_id,
            instrument_id=trade.contract.instrument_id, side=trade.side, quantity=trade.quantity,
            entry_price=trade.entry_price, entry_time=trade.entry_time, exit_price=trade.exit_price,
            exit_time=trade.exit_time, exit_order=record, exit_reason=trade.reason,
            gross_pnl=trade.gross, net_pnl=trade.net, charges_json=trade.charges,
            brokerage=brokerage, taxes=fees-brokerage,
            pnl_pct=100*trade.net/trade.contract.value(trade.entry_price, trade.quantity),
            holding_duration_seconds=max(int((trade.exit_time-trade.entry_time).total_seconds()), 0))
    PaperAccount.objects.filter(pk=state.key[1]).update(current_balance=result.balance, updated_at=timezone.now())
    return record


def _live(result: Transition, state: Account):
    from live_trading.models import ExecutionLog, LiveOrder, LivePosition, LiveTrade, SlippageRecord, TradingSession
    session = TradingSession.objects.get(pk=result.order.unit[1])
    order, position, trade = result.order, result.position, result.trade
    ownership = dict(user_id=session.user_id, strategy_id=session.strategy_id,
        allocation_id=session.allocation_id, broker_credential_id=state.key[1])
    defaults = {**ownership, 'session_id': session.pk, 'instrument_id': order.contract.instrument_id,
        'broker_order_id': order.broker_id, 'exchange_order_id': order.exchange_order_id,
        'broker_ordered_at': order.broker_ordered_at, 'broker_updated_at': order.broker_updated_at,
        'reason': order.reason[:255], 'order_type': order.order_type, 'product_type': order.contract.product,
        'side': order.side, 'quantity': order.quantity, 'price': order.price or order.reference_price,
        'filled_quantity': order.filled, 'pending_quantity': order.remaining if order.status in
            (OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, 'UNKNOWN') else 0,
        'filled_value': order.filled_value, 'avg_fill_price': order.filled_value/order.filled if order.filled else None,
        'strategy_version_id': order.version, 'intent': order.intent, 'status': order.status,
        'rejection_reason': order.error}
    if result.fill is not None:
        defaults['executed_at'] = result.fill.at
    if order.status == OrderStatus.CANCELLED:
        defaults['cancelled_at'] = order.broker_updated_at or timezone.now()
    previous = LiveOrder.objects.filter(request_id=order.identity).values('status', 'filled_quantity').first()
    record, created = LiveOrder.objects.update_or_create(request_id=order.identity, defaults=defaults)
    if created or previous['status'] != order.status or previous['filled_quantity'] != order.filled:
        ExecutionLog.objects.create(order=record, event_type='CREATED' if created else order.status,
            message=order.error or f'{order.reason}: {order.filled}/{order.quantity} filled')
    if result.fill is not None and order.reference_price > ZERO:
        average = order.filled_value / order.filled
        adverse = (average - order.reference_price) * (1 if order.side == Side.BUY else -1)
        SlippageRecord.objects.update_or_create(order=record, defaults={
            'expected_price': order.reference_price, 'actual_price': average,
            'slippage_pct': adverse / order.reference_price * 100,
            'slippage_amount': order.contract.value(adverse, order.filled)})
    owned = LivePosition.objects.filter(allocation_id=session.allocation_id,
                                        instrument_id=order.contract.instrument_id)
    if result.fill is not None:
        if position is None:
            owned.delete()
        else:
            row, _ = LivePosition.objects.update_or_create(allocation_id=session.allocation_id,
                instrument_id=order.contract.instrument_id, defaults={**ownership, 'product_type': order.contract.product,
                'side': Side.BUY if position.quantity > 0 else Side.SELL, 'quantity': abs(position.quantity),
                'avg_price': position.average, 'current_price': result.fill.price, 'unrealized_pnl': ZERO})
            owned.filter(pk=row.pk).update(opened_at=position.opened_at)
    if trade is not None:
        LiveTrade.objects.create(**ownership, instrument_id=trade.contract.instrument_id, exit_order=record,
            side=trade.side, quantity=trade.quantity, entry_price=trade.entry_price, entry_time=trade.entry_time,
            exit_price=trade.exit_price, exit_time=trade.exit_time, exit_reason=trade.reason,
            gross_pnl=trade.gross, realized_pnl=trade.net,
            holding_duration_seconds=max(int((trade.exit_time-trade.entry_time).total_seconds()), 0))
    return record


def _terminal(result: Transition, state: Account):
    from common.enums import OrderType, InstrumentType
    from trading.models import Account as AccountRecord, Order, Position, TradeHistory, ClosedPositionLog
    order, position, trade = result.order, result.position, result.trade
    kind = TerminalOrderType.STOP if order.order_type == OrderType.STOP_MARKET else order.order_type
    defaults = {'account_id': state.key[1], 'instrument_id': order.contract.instrument_id,
        'order_type': kind, 'status': TERMINAL_STATUS[order.status], 'transaction_type': order.side,
        'quantity': order.quantity, 'reserved_cash': order.reserved, 'price': order.price,
        'trigger_price': order.trigger, 'activated_at': order.activated_at,
        'filled_quantity': order.filled, 'avg_fill_price': order.filled_value/order.filled if order.filled else None,
        'rejection_reason': order.error[:255], 'reduce_only': order.reduce_only,
        'stop_loss': order.stop_loss, 'take_profit': order.take_profit,
        'charge_profile_snapshot': order.charge_profile, 'eligible_at': order.eligible_at}
    if result.fill is not None:
        defaults['executed_at'] = result.fill.at
    record, _ = Order.objects.update_or_create(request_id=order.identity, defaults=defaults)
    owned = Position.objects.filter(account_id=state.key[1], instrument_id=order.contract.instrument_id)
    previous_id = owned.values_list('pk', flat=True).first()
    if result.fill is not None:
        if position is None:
            owned.delete()
        else:
            row, _ = Position.objects.update_or_create(account_id=state.key[1], instrument_id=order.contract.instrument_id,
                defaults={'quantity': position.quantity, 'average_price': position.average,
                'stop_loss': position.stop_loss, 'take_profit': position.take_profit})
            owned.filter(pk=row.pk).update(created_at=position.opened_at)
        fees = Decimal(str(trade.charges.get('total_charges', 0))) if trade else ZERO
        history = TradeHistory.objects.create(order=record, executed_price=result.fill.price,
            quantity=result.fill.quantity, charges=fees, charges_breakdown=trade.charges if trade else {})
        TradeHistory.objects.filter(pk=history.pk).update(timestamp=result.fill.at)
    if trade is not None:
        ClosedPositionLog.objects.create(account_id=state.key[1], instrument_id=order.contract.instrument_id,
            side='LONG' if trade.side == Side.BUY else 'SHORT', quantity=trade.quantity,
            entry_price=trade.entry_price, exit_price=trade.exit_price, realized_pnl=trade.net,
            gross_pnl=trade.gross, recorded_charges=Decimal(str(trade.charges.get('total_charges', 0))),
            exit_reason=trade.reason[:100], entry_time=trade.entry_time, exit_time=trade.exit_time)
    # Existing Terminal API reports a cash balance. Convert the common owner's
    # settled equity at this boundary; the kernel has just one balance meaning.
    cash = state.balance - sum((p.contract.value(p.average, p.quantity) for p in state.positions.values()
                               if p.contract.instrument_type != InstrumentType.FUTURE), ZERO)
    collateral = sum((p.margin + p.contract.value(p.average, -p.quantity)
        if p.quantity < 0 and p.contract.instrument_type != InstrumentType.FUTURE else
        p.margin if p.contract.instrument_type == InstrumentType.FUTURE else ZERO
        for p in state.positions.values()), ZERO)
    AccountRecord.objects.filter(pk=state.key[1]).update(balance=cash, margin=collateral,
        realized_pnl=state.realized, charges_paid=state.charges_paid)
    from trading.signals import order_status_changed, position_changed
    order_status_changed.send(sender=Order, order=record)
    if result.fill is not None:
        from trading.serializers import PositionSerializer
        current = owned.first()
        position_changed.send(sender=Position, user_id=record.account.user_id,
            position_data=PositionSerializer(current).data if current else
            {'id': previous_id, 'instrument_id': order.contract.instrument_id, 'quantity': 0, 'deleted': True})
    return record


WRITERS = {ExecutionMode.PAPER: _paper, ExecutionMode.LIVE: _live, ExecutionMode.TERMINAL: _terminal}


@transaction.atomic
def persist_control(result):
    """Commit a user command and its configuration/funds effects as one operation."""
    command = Command.objects.select_for_update().get(pk=result.identity)
    if command.applied_at is not None:
        return
    row = AccountCheckpoint.objects.select_for_update().get(mode=command.mode, account_id=command.account_id)
    if not result.error:
        if result.account.revision != row.revision + 1:
            raise ValueError('Control command overtook an uncommitted financial transition.')
        state = deepcopy(result.account)
        state.committed_revision = state.revision
        state.pending_funds.clear()
        state.uncommitted_funds = ZERO
        row.state, row.revision = encode(state), state.revision
        row.save(update_fields=['state', 'revision', 'updated_at'])
        from common.enums import ExecutionCommandType
        if command.kind == ExecutionCommandType.REFRESH:
            from paper_trading.models import PaperTradingSession
            from live_trading.models import TradingSession
            if command.mode != ExecutionMode.TERMINAL:
                model = PaperTradingSession if command.mode == ExecutionMode.PAPER else TradingSession
                for session_id, version in state.versions.items():
                    session = model.objects.get(pk=session_id)
                    session.applied_version_id, session.applied_at = version, timezone.now()
                    session.save(update_fields=['applied_version', 'applied_at'])
                if 'allocation_changes' in command.payload:
                    from live_trading.models import LiveStrategyAllocation
                    LiveStrategyAllocation.objects.filter(session__pk=command.payload['session_id']).update(
                        **command.payload['allocation_changes'], is_over_allocated=False, breach_reason='', updated_at=timezone.now())
            elif 'terminal_changes' in command.payload:
                from trading.models import Account as AccountRecord
                from common.enums import InstrumentType
                changes = dict(command.payload['terminal_changes'])
                if 'charge_profile' in changes:
                    changes['charge_profile_id'] = changes.pop('charge_profile')
                changes['margin'] = sum((p.margin + p.contract.value(p.average, -p.quantity)
                    if p.quantity < 0 and p.contract.instrument_type != InstrumentType.FUTURE else
                    p.margin if p.contract.instrument_type == InstrumentType.FUTURE else ZERO
                    for p in state.positions.values()), ZERO)
                AccountRecord.objects.filter(pk=command.account_id).update(**changes)
                from common.channels import publish_trading_update
                from trading.serializers import AccountSerializer
                account = AccountRecord.objects.get(pk=command.account_id)
                publish_trading_update(f'user_{account.user_id}', 'ACCOUNT_UPDATE', dict(AccountSerializer(account).data))
        elif command.kind == ExecutionCommandType.PROTECT:
            from trading.models import Position
            from trading.serializers import PositionSerializer
            from trading.signals import position_changed
            unit = tuple(command.payload['unit'])
            position = state.positions[unit]
            Position.objects.filter(account_id=command.account_id, instrument_id=unit[2]).update(
                stop_loss=position.stop_loss, take_profit=position.take_profit)
            record = Position.objects.select_related('account', 'instrument').get(
                account_id=command.account_id, instrument_id=unit[2])
            position_changed.send(sender=Position, user_id=record.account.user_id,
                                  position_data=PositionSerializer(record).data)
        elif command.kind == ExecutionCommandType.BALANCE and command.mode == ExecutionMode.PAPER:
            from common.enums import TransactionType
            from paper_trading.models import PaperAccount, CapitalAllocation, Portfolio, FundTransaction
            PaperAccount.objects.filter(pk=command.account_id).update(current_balance=state.balance, updated_at=timezone.now())
            if 'allocation_amount' in command.payload:
                CapitalAllocation.objects.filter(pk=command.payload['allocation_id']).update(
                    allocated_amount=command.payload['allocation_amount'], updated_at=timezone.now())
            delta = Decimal(command.payload['delta'])
            if delta < 0:
                wallet = Portfolio.objects.select_for_update().get(pk=command.payload['portfolio_id'])
                before = wallet.current_capital
                wallet.current_capital -= delta
                wallet.save(update_fields=['current_capital', 'updated_at'])
                FundTransaction.objects.create(portfolio=wallet, transaction_type=TransactionType.DEALLOCATION,
                    amount=-delta, balance_before=before, balance_after=wallet.current_capital,
                    notes='Capital returned from deployment')
    command.applied_at, command.error = timezone.now(), result.error
    command.save(update_fields=['applied_at', 'error'])


@transaction.atomic
def persist_transition(result: Transition, *, command_id: int | None = None):
    checkpoint = AccountCheckpoint.objects.select_for_update().get(
        mode=result.account[0], account_id=result.account[1])
    if result.revision <= checkpoint.revision:
        return None  # A writer acknowledgement can be lost; committed effects are not repeated.
    if result.revision != checkpoint.revision + 1:
        raise ValueError('Financial transition sequence is incomplete; stop and recover the owner.')
    state = decode(checkpoint.state)
    state.revision = state.committed_revision = result.revision
    state.balance, state.realized, state.charges_paid = result.balance, result.realized, result.charges_paid
    state.orders[result.order.identity] = deepcopy(result.order)
    state.index_order(state.orders[result.order.identity])
    state.position_revisions[result.order.unit] = result.position_revision
    if result.position is None:
        state.positions.pop(result.order.unit, None)
    else:
        state.positions[result.order.unit] = deepcopy(result.position)
    if result.allocation is not None:
        state.allocations[result.order.unit[1]] = result.allocation
    if result.broker_debit:
        state.broker_spending[result.revision] = result.broker_debit
    record = WRITERS[result.account[0]](result, state)
    checkpoint.revision, checkpoint.state = result.revision, encode(state)
    checkpoint.save(update_fields=['revision', 'state', 'updated_at'])
    if command_id is not None:
        Command.objects.filter(pk=command_id, applied_at__isnull=True).update(applied_at=timezone.now())
    return record
