"""Settlement source validation and durable writes; controller/CLI use only.

An imported price is evidence, not permission to fabricate a broker fill. Paper
and Terminal accounts can consume reviewed simulation settlements. Live reports
remain separate until an account-specific broker source is qualified.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import NAMESPACE_URL, uuid5

from django.db import transaction
from django.utils import timezone

from common.enums import ExecutionCommandType as Kind, ExecutionMode as Mode, Exchange, ExchangeInstrumentType, FyersSegment, InstrumentType, SettlementKind
from instruments.models import Instrument
from marketdata.calendar import MarketSessionCalendar
from .models import AccountCheckpoint, Command, SettlementPosting, SettlementPrice
from .settlements import SettlementPrice as Price
from .snapshots import decode, encode
from .types import ZERO


def prepare_price(record, *, expiry=None):
    """Check expiry against the segment calendar, not a UTC date or cash hours."""
    instrument = record.instrument
    expiry = expiry if expiry is not None else instrument.expiry_date
    calendar = MarketSessionCalendar.for_instrument(instrument)
    day = record.effective_at.astimezone(calendar.zone).date()
    calendar.load_holidays(day, day)
    if not calendar.is_trading_day(day) or record.effective_at != calendar.session_close(day):
        raise ValueError('effective_at must be the exchange/segment session close.')
    if expiry is None or day > expiry:
        raise ValueError('Settlement requires known, unexpired contract terms at its cutoff.')
    if record.available_at < record.effective_at:
        raise ValueError('available_at cannot precede the settlement cutoff.')
    if not record.value.is_finite() or record.value < ZERO:
        raise ValueError('Settlement value must be finite and nonnegative.')
    if record.kind == SettlementKind.DAILY:
        if instrument.instrument_type != InstrumentType.FUTURE or record.value <= ZERO or day == expiry:
            raise ValueError('Daily MTM is for futures before expiry; expiry requires final settlement.')
        if record.cash_settled or record.fee_per_unit is not None:
            raise ValueError('Daily MTM must not include final-settlement flags or fees.')
    elif record.kind == SettlementKind.FINAL:
        if day != expiry:
            raise ValueError('Final settlement must use the actual contract expiry session.')
        # First qualified family: equity index derivatives. Stock delivery,
        # commodity devolvement and other clearing conventions are not guessed.
        if (not record.cash_settled or instrument.exchange not in (Exchange.NSE, Exchange.BSE)
                or instrument.segment != FyersSegment.EQUITY_DERIVATIVES or instrument.ex_inst_type not in
                (ExchangeInstrumentType.FUTIDX, ExchangeInstrumentType.OPTIDX)):
            raise ValueError('Final cash settlement is qualified only for index futures/options.')
        if record.fee_per_unit is None or record.fee_per_unit < ZERO or not record.fee_per_unit.is_finite():
            raise ValueError('Supply reviewed simulation settlement fees per unit, including entry costs.')
    else:
        raise ValueError('Unsupported settlement kind.')
    return Price(record.pk, instrument.pk, record.kind, record.value, record.effective_at,
                 record.available_at, record.source, record.cash_settled, record.fee_per_unit)


@transaction.atomic
def import_prices(document, *, dry_run=False):
    """Strict, all-or-nothing, idempotent import of reviewed source rows."""
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'source', 'prices'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1):
        raise ValueError('Provide schema_version: 1, source and prices.')
    source, rows = document['source'], document['prices']
    if not isinstance(source, str) or not source.strip() or len(source) > 500:
        raise ValueError('Provide a source reference of 1 to 500 characters.')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5000:
        raise ValueError('Import between 1 and 5000 prices.')
    fields = {'sym_ticker', 'kind', 'effective_at', 'available_at', 'value', 'cash_settled', 'fee_per_unit'}
    if any(not isinstance(row, dict) or set(row) != fields or not isinstance(row['sym_ticker'], str) for row in rows):
        raise ValueError(f'Each row needs exactly: {", ".join(sorted(fields))}.')
    instruments = {item.sym_ticker: item for item in Instrument.objects.select_for_update().filter(
        sym_ticker__in={row['sym_ticker'] for row in rows}).order_by('pk')}
    additions, seen, unchanged = [], set(), 0
    for index, row in enumerate(rows, 1):
        try:
            instrument = instruments.get(row['sym_ticker'])
            if instrument is None:
                raise ValueError('Unknown contract sym_ticker; import its sourced identity first.')
            values = {}
            for name in ('effective_at', 'available_at'):
                if not isinstance(row[name], str):
                    raise ValueError(f'{name} must be an ISO datetime.')
                values[name] = datetime.fromisoformat(row[name])
                if timezone.is_naive(values[name]):
                    raise ValueError(f'{name} must include a timezone offset.')
            for name in ('value', 'fee_per_unit'):
                value = row[name]
                if name == 'fee_per_unit' and value is None:
                    values[name] = None
                elif isinstance(value, str) and Decimal(value).is_finite():
                    values[name] = Decimal(value)
                else:
                    raise ValueError(f'{name} must be a finite decimal string.')
            if type(row['cash_settled']) is not bool or row['kind'] not in SettlementKind.values:
                raise ValueError('Choose a settlement kind and a boolean cash_settled value.')
            record = SettlementPrice(instrument=instrument, source=source.strip(),
                kind=row['kind'], cash_settled=row['cash_settled'], **values)
            record.clean_fields()
            prepare_price(record)
            identity = instrument.pk, record.effective_at, record.kind
            if identity in seen:
                raise ValueError('Duplicate contract/cutoff/kind in this batch.')
            seen.add(identity)
            previous = SettlementPrice.objects.filter(instrument=instrument,
                effective_at=record.effective_at, kind=record.kind).first()
            if previous is None:
                additions.append(record)
            elif any(getattr(previous, field) != getattr(record, field)
                     for field in ('source', 'available_at', 'value', 'cash_settled', 'fee_per_unit')):
                raise ValueError('Different evidence already exists. Review the correction; do not overwrite applied prices.')
            else:
                unchanged += 1
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(f'Settlement row {index}: {exc}') from None
    if not dry_run:
        SettlementPrice.objects.bulk_create(additions)
    return {'created': len(additions), 'unchanged': unchanged}


def command_values(command, *, now):
    record = SettlementPrice.objects.select_related('instrument').get(pk=command.payload['price_id'])
    unit = tuple(command.payload['unit'])
    if unit[0] != command.mode or (command.mode == Mode.TERMINAL and unit[1] != command.account_id):
        raise ValueError('Settlement ownership does not match its command.')
    return dict(unit=unit, price=prepare_price(record), now=now,
        quantity=command.payload['quantity'], opened_at=datetime.fromisoformat(command.payload['opened_at']))


def historical_prices(instrument, start, end, calendar, *, expiry, required=True):
    """Prove overnight/expiry accounting coverage before replay starts.

    A last-session position can close through the existing end-of-test policy.
    Earlier futures sessions require official MTM; expiry requires its final
    event. Publication time, not the retrospectively known price, clocks replay.
    """
    if instrument.instrument_type not in (InstrumentType.FUTURE, InstrumentType.OPTION):
        return ()
    start_day, end_day = start.astimezone(calendar.zone).date(), end.astimezone(calendar.zone).date()
    records = list(SettlementPrice.objects.select_related('instrument').filter(
        instrument=instrument, effective_at__gte=start, effective_at__lte=end))
    by_day = {(row.effective_at.astimezone(calendar.zone).date(), row.kind): row for row in records}
    prices = []
    for day in calendar._date_range(start_day, min(end_day, expiry)):
        if not calendar.is_trading_day(day):
            continue
        kind = (SettlementKind.FINAL if day == expiry else
                SettlementKind.DAILY if instrument.instrument_type == InstrumentType.FUTURE and day < end_day else None)
        if kind is None or calendar.session_close(day) > end:
            continue
        record = by_day.get((day, kind))
        if record is None or record.available_at > end:
            if not required:
                continue
            raise ValueError(f'{instrument.name}: sourced {kind} settlement is missing or unavailable by replay end for {day}.')
        prices.append(prepare_price(record, expiry=expiry))
    return tuple(sorted(prices, key=lambda item: (item.available_at, item.identity)))


def queue_settlements(accounts):
    """Cold, periodic catch-up; one deterministic command per record/position cycle.

    Rejected historical reports remain visible as rejected commands. They are not
    retried against a different quantity or silently applied to a later position.
    """
    now = timezone.now()
    calendars = {}
    for mode, account_id in accounts:
        if mode not in (Mode.PAPER, Mode.TERMINAL):
            continue
        checkpoint = AccountCheckpoint.objects.filter(mode=mode, account_id=account_id).first()
        if checkpoint is None:
            continue
        state = decode(checkpoint.state)
        # Expiry does not need another quote. Cancel simulated working orders
        # before queuing final settlement, even if source publication is late.
        for order in state.working.values():
            contract = order.contract
            if contract.expiry is None or contract.expiry > now.date():
                continue
            if contract.instrument_id not in calendars:
                instrument = Instrument.objects.get(pk=contract.instrument_id)
                calendar = MarketSessionCalendar.for_instrument(instrument)
                calendar.load_holidays(contract.expiry, contract.expiry)
                calendars[contract.instrument_id] = calendar
            if now < calendars[contract.instrument_id].session_close(contract.expiry):
                continue
            request_id = uuid5(NAMESPACE_URL, f'quantnest:expiry:{mode}:{account_id}:{order.identity}')
            Command.objects.get_or_create(request_id=request_id, defaults=dict(mode=mode, account_id=account_id,
                kind=Kind.CANCEL, payload={'identity': order.identity, 'reason': 'Contract expired.'}))
        for unit, position in state.positions.items():
            records = SettlementPrice.objects.filter(instrument_id=position.contract.instrument_id,
                effective_at__gte=position.opened_at, available_at__lte=now)
            if position.settled_at:
                records = records.filter(effective_at__gt=position.settled_at)
            for record in records:
                identity = f'{record.pk}:{unit[0]}:{unit[1]}:{unit[2]}:{unit[3]}:{position.opened_at.isoformat()}'
                if identity in state.settlements:
                    continue
                request_id = uuid5(NAMESPACE_URL, f'quantnest:settlement:{account_id}:{identity}')
                Command.objects.get_or_create(request_id=request_id, defaults=dict(mode=mode,
                    account_id=account_id, kind=Kind.SETTLEMENT, payload={
                        'price_id': record.pk, 'unit': list(unit), 'quantity': position.quantity,
                        'opened_at': position.opened_at.isoformat()}))


@transaction.atomic
def persist_settlement(message):
    """The journal, read models, command and checkpoint commit together."""
    command = Command.objects.select_for_update().get(pk=message.identity)
    if command.applied_at is not None:
        return
    checkpoint = AccountCheckpoint.objects.select_for_update().get(mode=command.mode, account_id=command.account_id)
    result, state = message.result, deepcopy(message.account)
    if result is not None:
        if state.revision != checkpoint.revision + 1:
            raise ValueError('Settlement overtook an uncommitted account transition.')
        SettlementPosting.objects.create(identity=result.identity, price_id=result.price_id,
            command=command, mode=command.mode, account_id=command.account_id, session_id=result.unit[1],
            route_id=result.unit[2], leg_id=result.unit[3],
            quantity=result.quantity, opened_at=result.opened_at, gross=result.gross, fees=result.fees,
            cash_change=result.cash_change, revision=state.revision)
        project_settlement(state, result)
        state.committed_revision = state.revision
        state.pending_funds.clear()
        state.uncommitted_funds = ZERO
        checkpoint.state, checkpoint.revision = encode(state), state.revision
        checkpoint.save(update_fields=['state', 'revision', 'updated_at'])
    command.applied_at = timezone.now()
    command.save(update_fields=['applied_at'])


def project_settlement(state, result):
    """Settlement has no fictitious order, trade fill, turnover or broker call."""
    from common.enums import Side, TerminalExitReason
    from .repository import terminal_account_values
    from paper_trading.models import PaperAccount, PaperPosition, PaperTrade, PaperTradingSession
    from trading.models import Account, Position, ClosedPositionLog
    mode, account_id = state.key
    instrument_id = SettlementPrice.objects.values_list('instrument_id', flat=True).get(pk=result.price_id)
    position, trade = state.positions.get(result.unit), result.trade
    if mode == Mode.PAPER:
        owned = PaperPosition.objects.filter(account_id=account_id, route_id=result.unit[2], leg_id=result.unit[3])
        PaperAccount.objects.filter(pk=account_id).update(current_balance=state.balance)
        if position is not None:
            from django.db.models import F
            # A mark can be older than the settlement price. Keep its observed
            # price/time and remove only the additional amount now paid to cash.
            owned.update(settled_pnl=position.settled_pnl, unrealized_pnl=F('unrealized_pnl')-result.gross)
        else:
            session = PaperTradingSession.objects.get(pk=result.unit[1])
            owned.delete()
            PaperTrade.objects.create(account_id=account_id, strategy_id=session.strategy_id,
                route_id=trade.unit[2], leg_id=trade.unit[3],
                instrument_id=instrument_id, side=trade.side, quantity=trade.quantity,
                entry_price=trade.entry_price, entry_time=trade.entry_time,
                exit_price=trade.exit_price, exit_time=trade.exit_time, exit_reason=trade.reason,
                gross_pnl=trade.gross, net_pnl=trade.net, settled_pnl=trade.settled_pnl,
                taxes=result.fees, charges_json=trade.charges,
                pnl_pct=100*trade.net/trade.contract.value(trade.entry_price, trade.quantity),
                holding_duration_seconds=max(int((trade.exit_time-trade.entry_time).total_seconds()), 0))
        from common.channels import publish_trading_update
        from paper_trading.serializers import PaperPositionSerializer
        account = PaperAccount.objects.get(pk=account_id)
        current = owned.first()
        if current is not None:
            publish_trading_update(f'user_{account.user_id}_paper', 'POSITION_UPDATE', PaperPositionSerializer(current).data)
        publish_trading_update(f'user_{account.user_id}_paper', 'SESSION_UPDATE', {'id': result.unit[1], 'settlement': result.price_id})
    elif mode == Mode.TERMINAL:
        owned = Position.objects.filter(account_id=account_id, instrument_id=instrument_id)
        previous_id = owned.values_list('pk', flat=True).first()
        if position is not None:
            owned.update(settled_pnl=position.settled_pnl)
        else:
            owned.delete()
            closed = ClosedPositionLog.objects.create(account_id=account_id, instrument_id=instrument_id,
                side='LONG' if trade.side == Side.BUY else 'SHORT', quantity=trade.quantity,
                entry_price=trade.entry_price, exit_price=trade.exit_price, gross_pnl=trade.gross,
                realized_pnl=trade.net, recorded_charges=result.fees, exit_reason=TerminalExitReason.OFFICIAL_SETTLEMENT,
                entry_time=trade.entry_time, exit_time=trade.exit_time)
            ClosedPositionLog.objects.filter(pk=closed.pk).update(exit_time=trade.exit_time)
        Account.objects.filter(pk=account_id).update(**terminal_account_values(state))
        from common.channels import publish_trading_update
        from trading.serializers import AccountSerializer, PositionSerializer
        account = Account.objects.get(pk=account_id)
        current = owned.first()
        publish_trading_update(f'user_{account.user_id}', 'ACCOUNT_UPDATE', AccountSerializer(account).data)
        publish_trading_update(f'user_{account.user_id}', 'POSITION_UPDATE', PositionSerializer(current).data if current else
            {'id': previous_id, 'instrument_id': instrument_id, 'quantity': 0, 'deleted': True})
    else:
        raise ValueError('No settlement projection is qualified for this deployment mode.')
