"""Load account ownership and existing records once before workers start.

After the first checkpoint, financial recovery uses that committed checkpoint.
Model queries here also supply session configuration to the admission thread;
they are never part of an observation or fill calculation.
"""
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from common.costs import snapshot_charge_profile
from common.enums import ExecutionMode, ExecutionSessionStatus, InstrumentType, OrderIntent, OrderType, Side, TerminalOrderType
from instruments.services import InstrumentResolver

from .ledger import ACTIVE_STATUSES, margin
from .preparation import contract_from_instrument
from .repository import initialize_account, restore_account
from .types import Account, EntryLot, Order, Position, ZERO, route_key, terminal_key


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
            sizing = InstrumentResolver.sizing_for(watch, config['position_sizing_rule'])
            account.sizing[route_key(account.key[0], session.pk, watch)] = sizing
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
        unit = mode, session.pk, record.route_id, record.leg_id
        watch = next(item for item in session.allocation.deployed_version.config_snapshot['watchlist_instruments']
                     if (item['route_id'], item['leg_id']) == unit[2:])
        binding = InstrumentResolver.input_bindings(watch)
        quantity = record.quantity if record.side == Side.BUY else -record.quantity
        lot = EntryLot(record.quantity, record.avg_price, record.opened_at,
            f'recovered:{mode}:{record.pk}', account.profiles.get(session.pk, {}), record.quantity)
        position = Position(unit, contract, quantity, record.avg_price, record.opened_at,
            revision=1, margin=record.margin_blocked, lots=[lot], peak=float(record.avg_price),
            settled_pnl=record.settled_pnl, binding=(binding['signal'], contract.instrument_id))
        owner_filter = {'account_id': identity} if mode == ExecutionMode.PAPER else {'allocation_id': record.allocation_id}
        last_fill = (PaperOrder if mode == ExecutionMode.PAPER else LiveOrder).objects.filter(
            **owner_filter, route_id=record.route_id, leg_id=record.leg_id,
            instrument_id=record.instrument_id, executed_at__gte=record.opened_at
        ).order_by('-executed_at').values_list('executed_at', flat=True).first()
        position.last_fill_at = last_fill or position.opened_at
        account.positions[unit], account.position_revisions[unit] = position, 1
    for record in orders.select_related('instrument'):
        session = sessions[0] if mode == ExecutionMode.PAPER else session_by_allocation[record.allocation_id]
        contract = contract_from_instrument(record.instrument)
        unit = mode, session.pk, record.route_id, record.leg_id
        watch = next(item for item in session.allocation.deployed_version.config_snapshot['watchlist_instruments']
                     if (item['route_id'], item['leg_id']) == unit[2:])
        binding = InstrumentResolver.input_bindings(watch)
        filled_value = record.filled_quantity * (record.avg_fill_price or ZERO)
        order = Order(str(record.request_id), unit, contract, record.side, record.quantity,
            record.created_at, record.reason, order_type=record.order_type, price=record.price,
            filled=record.filled_quantity, filled_value=filled_value, status=record.status,
            version=account.versions[session.pk], charge_profile=account.profiles.get(session.pk, {}),
            binding=(binding['signal'], contract.instrument_id))
        if mode == ExecutionMode.LIVE:
            order.intent, order.broker_id = record.intent, record.broker_order_id
            order.version = record.strategy_version_id
            order.broker_ordered_at, order.broker_updated_at = record.broker_ordered_at, record.broker_updated_at
            order.exchange_order_id = record.exchange_order_id
        else:
            order.intent = OrderIntent(record.order_tag)
        order.reduce_only = order.intent == OrderIntent.EXIT
        order.reserved = record.reserved_capital
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
        unit = terminal_key(identity, row.instrument_id)
        position = Position(unit, contract, row.quantity, row.average_price, row.created_at,
            revision=1, margin=margin(account, contract, row.quantity, row.average_price),
            stop_loss=row.stop_loss, take_profit=row.take_profit, peak=float(row.average_price),
            settled_pnl=row.settled_pnl, binding=(row.instrument_id, row.instrument_id))
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
        position.last_fill_at = max(fill.timestamp for fill in fills)
        account.positions[unit], account.position_revisions[unit] = position, 1
        if contract.instrument_type != InstrumentType.FUTURE:
            account.balance += contract.value(row.average_price, row.quantity)
    from .models import Command
    from common.enums import ExecutionCommandType
    queued = Command.objects.filter(mode=ExecutionMode.TERMINAL, account_id=identity,
        kind=ExecutionCommandType.ORDER, applied_at__isnull=True).values('request_id')
    for row in OrderRecord.objects.filter(account_id=identity, status=TerminalOrderStatus.OPEN).exclude(
            request_id__in=queued).select_related('instrument'):
        if row.request_id is None:
            row.request_id = uuid5(NAMESPACE_URL, f'quantnest:terminal:order:{row.pk}')
            row.save(update_fields=['request_id'])
        kind = OrderType.STOP_MARKET if row.order_type == TerminalOrderType.STOP else row.order_type
        unit = terminal_key(identity, row.instrument_id)
        account.orders[str(row.request_id)] = Order(str(row.request_id), unit, contract_from_instrument(row.instrument),
            row.transaction_type, row.quantity, row.eligible_at, 'Manual order', order_type=kind,
            price=row.price, trigger=row.trigger_price, reduce_only=row.reduce_only,
            activated_at=row.activated_at, filled=row.filled_quantity,
            filled_value=(row.avg_fill_price or ZERO)*row.filled_quantity, reserved=row.reserved_cash,
            stop_loss=row.stop_loss, take_profit=row.take_profit, charge_profile=row.charge_profile_snapshot,
            manual=True, binding=(row.instrument_id, row.instrument_id))
    return account


def recover_account(key) -> Account:
    stored = restore_account(key)
    if stored is not None:
        return stored
    account = _terminal_account(key[1]) if key[0] == ExecutionMode.TERMINAL else _strategy_account(key)
    from .models import SettlementPosting
    # Reconstruct settlement chronology only at cold recovery. A later source
    # revision cannot be applied to units already marked at a newer cutoff.
    for unit, position in account.positions.items():
        posting = SettlementPosting.objects.filter(mode=key[0], account_id=key[1], session_id=unit[1],
            price__instrument_id=position.contract.instrument_id, opened_at=position.opened_at,
            route_id=unit[2], leg_id=unit[3]
        ).select_related('price').order_by('-price__effective_at').first()
        if posting is not None:
            position.settled_at = posting.price.effective_at
    return initialize_account(account)


def load_configuration(key, *, instrument_ids=(), committed=False):
    """Compile immutable inputs off the CPU workers, once per configuration change."""
    from django.utils import timezone
    from instruments.models import Instrument
    from marketdata.calendar import MarketSessionCalendar

    state = restore_account(key)
    ids = set(instrument_ids)
    if state:
        ids.update(position.contract.instrument_id for position in state.positions.values())
        ids.update(order.contract.instrument_id for order in state.orders.values() if order.status in ACTIVE_STATUSES)
    sessions, programs, bindings, input_programs = {}, {}, {}, {}
    prepared_calendars = {}
    today = timezone.localdate()
    from .preparation import compile_markets
    for session in sessions_for_account(key):
        version = session.allocation.deployed_version
        status = session.status
        if committed and state is not None:
            # Startup restores the version actually owned by this checkpoint.
            # A newer user request may still be pending or may have been rejected.
            applied = state.versions.get(session.pk, version.pk)
            if applied != version.pk:
                from strategies.models import StrategyVersion
                version = StrategyVersion.objects.get(pk=applied, strategy_id=session.strategy_id)
            status = state.statuses.get(session.pk, status)
        snapshot = version.config_snapshot
        retained = {}
        if state:
            for owned in (*state.positions.values(), *state.working.values()):
                if owned.unit[1] == session.pk:
                    retained.setdefault(owned.unit[2:], set()).add(owned.contract.instrument_id)
        compiled = compile_markets(snapshot, version.pk, retained=retained)
        for identity, calendar in compiled.calendars.items():
            # Both numerical preparation and admission carry holiday-aware
            # calendars into workers; the event loop never queries holidays.
            calendar.load_holidays(today-timedelta(days=7), today+timedelta(days=31))
            prepared_calendars[identity] = calendar
        sizing = {}
        for watch in snapshot['watchlist_instruments']:
            rule = InstrumentResolver.sizing_for(watch, snapshot['position_sizing_rule'])
            unit = route_key(key[0], session.pk, watch)
            route = unit[2:]
            if status != ExecutionSessionStatus.STOPPED:
                program = compiled.programs[route]
                binding = compiled.bindings[route]
                sources = {'signal': compiled.instruments[binding['signal']].sym_ticker}
                if program.selection is not None:
                    from dataclasses import replace
                    owned = state.positions.get(unit) if state else None
                    working = next((order for order in state.working.values() if order.unit == unit), None) if state else None
                    pinned = owned or working
                    if pinned is not None:
                        program = replace(program, binding=(program.binding[0], pinned.contract.instrument_id))
                    ids.update(program.candidates)
                    sources.update({str(identity): symbol for identity, symbol in program.candidates.items()})
                else:
                    ids.add(binding['trade'])
                    sources['trade'] = compiled.instruments[binding['trade']].sym_ticker
                programs[unit], bindings[unit] = program, sources
                for role, symbol in sources.items():
                    projection = program
                    if program.selection is not None or binding['signal'] != binding['trade']:
                        projection = projection.for_source('signal' if role == 'signal' else 'trade')
                    input_programs.setdefault(symbol, {})[unit] = projection
            sizing[unit] = rule
        paper = key[0] == ExecutionMode.PAPER
        sessions[session.pk] = dict(version=version.pk,
            status=status, sizing=sizing,
            profile=session.charge_profile_snapshot if paper and session.include_charges else {},
            slippage=session.slippage_pct if paper else ZERO,
            capital=None if paper else session.allocation.allocated_capital,
            close_on_stop=bool(state and session.status == ExecutionSessionStatus.STOPPING
                              and state.close_on_stop.get(session.pk, False)))
    contracts, calendars = {}, {}
    for instrument in Instrument.objects.filter(pk__in=ids):
        contract = contract_from_instrument(instrument)
        calendar = prepared_calendars.get(instrument.pk)
        if calendar is None:
            calendar = MarketSessionCalendar.for_instrument(instrument)
            calendar.load_holidays(today-timedelta(days=7), today+timedelta(days=31))
        contracts[instrument.pk], calendars[contract.symbol] = contract, calendar
    result = dict(sessions=sessions, contracts=contracts, calendars=calendars, programs=programs,
                  bindings=bindings, input_programs=input_programs)
    if key[0] == ExecutionMode.TERMINAL:
        from trading.models import Account as AccountRecord
        record = AccountRecord.objects.select_related('charge_profile').get(pk=key[1])
        result['terminal'] = dict(profile=snapshot_charge_profile(record.charge_profile),
            futures_margin_pct=record.futures_margin_pct, short_option_margin_pct=record.short_option_margin_pct)
    return result
