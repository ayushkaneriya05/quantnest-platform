"""Load account ownership and existing records once before workers start.

After the first checkpoint, financial recovery uses that committed checkpoint.
Model queries here also supply session configuration to the admission thread;
they are never part of an observation or fill calculation.
"""
from copy import deepcopy
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from common.costs import snapshot_charge_profile
from common.enums import ExecutionMode, ExecutionSessionStatus, InstrumentType, OrderIntent, OrderType, Side, TerminalOrderType
from instruments.services import InstrumentResolver

from .ledger import ACTIVE_STATUSES, margin
from .preparation import contract_from_instrument
from .repository import initialize_account, restore_account
from .types import Account, EntryLot, Order, Position, ZERO


def sessions_for_account(key):
    from paper_trading.models import PaperTradingSession
    from live_trading.models import TradingSession
    mode, identity = key
    if mode == ExecutionMode.TERMINAL:
        return []
    query = (PaperTradingSession.objects.filter(account_id=identity) if mode == ExecutionMode.PAPER
             else TradingSession.objects.filter(broker_credential_id=identity))
    return list(query.select_related('allocation__deployed_version', 'strategy').order_by('pk'))


def configure_sessions(account: Account, sessions) -> None:
    """Initial preparation only; running owners apply ordered configuration commands."""
    for session in sessions:
        config = session.allocation.deployed_version.config_snapshot
        account.versions[session.pk] = session.allocation.deployed_version_id
        account.statuses[session.pk] = session.status
        for watch in config['watchlist_instruments']:
            instrument_id, _, sizing = InstrumentResolver.resolve(watch,
                config['entry_order_config']['entry_side'], config['position_sizing_rule'])
            account.sizing[account.key[0], session.pk, instrument_id] = sizing
        if account.key[0] == ExecutionMode.PAPER:
            account.profiles[session.pk] = session.charge_profile_snapshot if session.include_charges else {}
            account.slippage[session.pk] = session.slippage_pct
        else:
            account.allocations[session.pk] = session.allocation.allocated_capital + session.allocation.realized_pnl
            account.allocation_principal[session.pk] = session.allocation.allocated_capital


def _strategy_account(key) -> Account:
    from brokers.models import BrokerFundsSnapshot
    from paper_trading.models import PaperAccount, PaperPosition, PaperOrder
    from live_trading.models import LivePosition, LiveOrder
    mode, identity = key
    sessions = sessions_for_account(key)
    if mode == ExecutionMode.PAPER:
        account = Account(key, PaperAccount.objects.get(pk=identity).current_balance)
        positions = PaperPosition.objects.filter(account_id=identity)
        orders = PaperOrder.objects.filter(account_id=identity, status__in=ACTIVE_STATUSES)
        session_by_allocation = {session.allocation_id: session for session in sessions}
    else:
        funds = BrokerFundsSnapshot.objects.filter(credential_id=identity).first()
        if funds is None:
            raise ValueError('Load a broker funds snapshot before starting this account.')
        account = Account(key, funds.net_equity, broker_available=funds.available_margin,
                          broker_observed_at=funds.snapshot_time)
        positions = LivePosition.objects.filter(broker_credential_id=identity)
        orders = LiveOrder.objects.filter(broker_credential_id=identity, status__in=ACTIVE_STATUSES)
        session_by_allocation = {session.allocation_id: session for session in sessions}
    configure_sessions(account, sessions)
    for record in positions.select_related('instrument').filter(quantity__gt=0):
        session = sessions[0] if mode == ExecutionMode.PAPER else session_by_allocation[record.allocation_id]
        contract = contract_from_instrument(record.instrument)
        unit = mode, session.pk, record.instrument_id
        quantity = record.quantity if record.side == Side.BUY else -record.quantity
        lot = EntryLot(record.quantity, record.avg_price, record.opened_at,
            f'recovered:{mode}:{record.pk}', account.profiles.get(session.pk, {}), record.quantity)
        position = Position(unit, contract, quantity, record.avg_price, record.opened_at,
            revision=1, margin=margin(account, contract, quantity, record.avg_price), lots=[lot], peak=float(record.avg_price))
        account.positions[unit], account.position_revisions[unit] = position, 1
    for record in orders.select_related('instrument'):
        session = sessions[0] if mode == ExecutionMode.PAPER else session_by_allocation[record.allocation_id]
        contract = contract_from_instrument(record.instrument)
        unit = mode, session.pk, record.instrument_id
        filled_value = record.filled_quantity * (record.avg_fill_price or ZERO)
        order = Order(str(record.request_id), unit, contract, record.side, record.quantity,
            record.created_at, record.reason, order_type=record.order_type, price=record.price,
            filled=record.filled_quantity, filled_value=filled_value, status=record.status,
            version=account.versions[session.pk], charge_profile=account.profiles.get(session.pk, {}))
        if mode == ExecutionMode.LIVE:
            order.intent, order.broker_id = record.intent, record.broker_order_id
            order.version = record.strategy_version_id
            order.broker_ordered_at, order.broker_updated_at = record.broker_ordered_at, record.broker_updated_at
            order.exchange_order_id = record.exchange_order_id
        else:
            order.intent = OrderIntent.EXIT if record.order_tag == 'strategy_exit' else OrderIntent.ENTRY
        order.reduce_only = order.intent == OrderIntent.EXIT
        if not order.reduce_only:
            order.reserved = contract.value(order.price, order.remaining)
        account.orders[order.identity] = order
    return account


def _terminal_account(identity: int) -> Account:
    from trading.models import Account as AccountRecord, Position as PositionRecord, Order as OrderRecord, TradeHistory
    from common.enums import TerminalOrderStatus
    record = AccountRecord.objects.select_related('charge_profile').get(pk=identity)
    account = Account((ExecutionMode.TERMINAL, identity), record.balance,
        realized=record.realized_pnl, charges_paid=record.charges_paid,
        profiles={identity: snapshot_charge_profile(record.charge_profile)},
        futures_margin_pct=record.futures_margin_pct, short_option_margin_pct=record.short_option_margin_pct)
    for row in PositionRecord.objects.filter(account_id=identity).select_related('instrument'):
        contract = contract_from_instrument(row.instrument)
        unit = ExecutionMode.TERMINAL, identity, row.instrument_id
        position = Position(unit, contract, row.quantity, row.average_price, row.created_at,
            revision=1, margin=margin(account, contract, row.quantity, row.average_price),
            stop_loss=row.stop_loss, take_profit=row.take_profit, peak=float(row.average_price))
        fills = list(TradeHistory.objects.filter(order__account_id=identity,
            order__instrument_id=row.instrument_id, timestamp__gte=row.created_at)
            .select_related('order').order_by('timestamp', 'pk'))
        if not fills:
            raise ValueError(f'Terminal position {row.pk} has no recoverable entry fills.')
        later = sum(fill.quantity * (1 if fill.order.transaction_type == Side.BUY else -1) for fill in fills[1:])
        for index, fill in enumerate(fills):
            same = (fill.order.transaction_type == Side.BUY) == (row.quantity > 0)
            if same:
                quantity = abs(row.quantity-later) if index == 0 else fill.quantity
                position.lots.append(EntryLot(quantity, fill.executed_price, fill.order.executed_at,
                    str(fill.order.pk), fill.order.charge_profile_snapshot, fill.quantity))
            else:
                from dataclasses import replace
                remaining, kept = fill.quantity, []
                for lot in sorted(position.lots, key=lambda item: (
                    item.at.astimezone().date() != fill.order.executed_at.astimezone().date(), item.at)):
                    used = min(remaining, lot.quantity)
                    remaining -= used
                    if lot.quantity > used:
                        kept.append(replace(lot, quantity=lot.quantity-used))
                position.lots = kept
        if sum(lot.quantity for lot in position.lots) != abs(row.quantity):
            raise ValueError(f'Terminal position {row.pk} has inconsistent entry fills.')
        account.positions[unit], account.position_revisions[unit] = position, 1
        if contract.instrument_type != InstrumentType.FUTURE:
            account.balance += contract.value(row.average_price, row.quantity)
    from .models import Command
    from common.enums import ExecutionCommandType
    queued = Command.objects.filter(mode=ExecutionMode.TERMINAL, account_id=identity,
        kind__in=(ExecutionCommandType.ORDER, ExecutionCommandType.SETTLE), applied_at__isnull=True).values('request_id')
    for row in OrderRecord.objects.filter(account_id=identity, status=TerminalOrderStatus.OPEN).exclude(
            request_id__in=queued).select_related('instrument'):
        if row.request_id is None:
            row.request_id = uuid5(NAMESPACE_URL, f'quantnest:terminal:order:{row.pk}')
            row.save(update_fields=['request_id'])
        kind = OrderType.STOP_MARKET if row.order_type == TerminalOrderType.STOP else row.order_type
        unit = ExecutionMode.TERMINAL, identity, row.instrument_id
        account.orders[str(row.request_id)] = Order(str(row.request_id), unit, contract_from_instrument(row.instrument),
            row.transaction_type, row.quantity, row.eligible_at, 'Manual order', order_type=kind,
            price=row.price, trigger=row.trigger_price, reduce_only=row.reduce_only,
            activated_at=row.activated_at, filled=row.filled_quantity,
            filled_value=(row.avg_fill_price or ZERO)*row.filled_quantity, reserved=row.reserved_cash,
            stop_loss=row.stop_loss, take_profit=row.take_profit, charge_profile=row.charge_profile_snapshot,
            manual=True)
    return account


def recover_account(key) -> Account:
    stored = restore_account(key)
    if stored is not None:
        return stored
    account = _terminal_account(key[1]) if key[0] == ExecutionMode.TERMINAL else _strategy_account(key)
    return initialize_account(account)


def load_configuration(key, *, instrument_ids=()):
    """Compile immutable inputs off the CPU workers, once per configuration change."""
    from django.utils import timezone
    from instruments.models import Instrument
    from marketdata.calendar import MarketSessionCalendar
    from .compiler import compile_strategy

    state = restore_account(key)
    ids = set(instrument_ids)
    if state:
        ids.update(unit[2] for unit in state.positions)
        ids.update(order.contract.instrument_id for order in state.orders.values() if order.status in ACTIVE_STATUSES)
    sessions, definitions = {}, {}
    for session in sessions_for_account(key):
        snapshot = session.allocation.deployed_version.config_snapshot
        sizing = {}
        for watch in snapshot['watchlist_instruments']:
            instrument_id, side, rule = InstrumentResolver.resolve(watch,
                snapshot['entry_order_config']['entry_side'], snapshot['position_sizing_rule'])
            unit = key[0], session.pk, instrument_id
            config = deepcopy(snapshot)
            config['entry_order_config']['entry_side'] = side
            if session.status != ExecutionSessionStatus.STOPPED:
                ids.add(instrument_id)
                definitions[unit] = session.allocation.deployed_version_id, config
            sizing[unit] = rule
        paper = key[0] == ExecutionMode.PAPER
        sessions[session.pk] = dict(version=session.allocation.deployed_version_id,
            status=session.status, sizing=sizing,
            profile=session.charge_profile_snapshot if paper and session.include_charges else {},
            slippage=session.slippage_pct if paper else ZERO,
            capital=None if paper else session.allocation.allocated_capital,
            close_on_stop=bool(state and session.status == ExecutionSessionStatus.STOPPING
                              and state.close_on_stop.get(session.pk, False)))
    contracts, calendars, programs = {}, {}, {}
    today = timezone.localdate()
    for instrument in Instrument.objects.filter(pk__in=ids):
        contract = contract_from_instrument(instrument)
        calendar = MarketSessionCalendar.for_instrument(instrument)
        calendar.load_holidays(today-timedelta(days=7), today+timedelta(days=31))
        contracts[instrument.pk], calendars[contract.symbol] = contract, calendar
    for unit, (version, config) in definitions.items():
        programs[unit] = compile_strategy(config, version, calendar=calendars[contracts[unit[2]].symbol])
    result = dict(sessions=sessions, contracts=contracts, calendars=calendars, programs=programs)
    if key[0] == ExecutionMode.TERMINAL:
        from trading.models import Account as AccountRecord
        record = AccountRecord.objects.select_related('charge_profile').get(pk=key[1])
        result['terminal'] = dict(profile=snapshot_charge_profile(record.charge_profile),
            futures_margin_pct=record.futures_margin_pct, short_option_margin_pct=record.short_option_margin_pct)
    return result
