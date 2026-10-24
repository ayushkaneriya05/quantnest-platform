"""Cold execution boundary: load commands, prepare inputs, commit effects and do I/O.

CPU workers own the numerical/account state. This process handles Django and
delegates warmup and broker network calls to a small thread pool. No worker waits
for another strategy's result or for a broker HTTP response.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as utc
from decimal import Decimal
import logging
from queue import Empty
import time

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Min
from django.utils import timezone

from common.enums import ExecutionCommandType as Kind, ExecutionMode as Mode, ExecutionSessionStatus as Status, OrderIntent, OrderType, TerminalOrderType
from marketdata.shared_memory import SharedMemoryManager

from .ledger import position_view
from .market import prepare_symbol
from .messages import (Committed, Control, EvaluationSaved, InstallAccount, InstallUnit, Persist, PrepareMarket,
    RemoveAccount, RemoveUnit, SaveControl, SessionSettled, UnitFailure)
from .models import Command
from .recovery import load_configuration, recover_account
from .repository import enqueue, persist_control, persist_transition
from .types import ACTIVE_STATUSES, Intent
from .worker import partition

logger = logging.getLogger(__name__)


def latest_observation(symbol):
    """Read an actual provider observation for an external command, never HTTP LTP."""
    buffer = SharedMemoryManager(symbol, '1m')
    try:
        if buffer.get_latest_price() is None:
            raise ValueError('Wait for a price observation from the connected feed.')
        snapshot = buffer.snapshot(1)
        rows, _, _, generation = buffer.read_observations(max(snapshot.sequence-1, 0), 1)
        if not len(rows):
            raise ValueError('Wait for a live price observation.')
        sequence, event, received, price, _ = rows[-1]
        return dict(sequence=int(sequence)*2, generation=generation,
            observed_at=datetime.fromtimestamp(event, utc.utc), reference_price=Decimal(str(price)))
    finally:
        buffer.close()


def broker_call(order_id, *, cancel=False):
    """An UNKNOWN owned order already exists durably before this function starts.

    A transport failure never resubmits the order. REST/order-stream reconciliation
    resolves the existing broker tag through the ordinary observation command.
    """
    from brokers.services import BrokerService
    from live_trading.models import LiveOrder
    close_old_connections()
    try:
        order = LiveOrder.objects.select_related('broker_credential', 'instrument').get(pk=order_id)
        if cancel:
            if order.broker_order_id:
                response = BrokerService.cancel_order(order.broker_credential, order.broker_order_id)
                if not response['accepted']:
                    logger.warning('Broker cancellation not accepted order=%s: %s', order_id, response['message'])
            return
        result = BrokerService.place_order(order.broker_credential, {
            'instrument': order.instrument.sym_ticker, 'side': order.side, 'quantity': order.quantity,
            'order_type': order.order_type, 'product_type': order.product_type,
            'validity': 'DAY', 'order_tag': f'QN{order.pk}',
        })
        enqueue(Mode.LIVE, order.broker_credential_id, Kind.BROKER, {
            'identity': str(order.request_id), 'broker_id': result.get('broker_order_id') or '',
            'status': result.get('status') or 'UNKNOWN', 'quantity': 0, 'average': '0',
            'at': timezone.now().isoformat(), 'error': result.get('message') or '',
        })
    except Exception:
        logger.exception('Broker operation needs reconciliation order=%s cancel=%s', order_id, cancel)
    finally:
        close_old_connections()


class Controller:
    def __init__(self, inboxes, output):
        self.inboxes, self.output = inboxes, output
        self.accounts = set()
        self.pending = {}  # account -> one in-flight external command
        self.configurations = {}  # command -> prepared configuration
        self.programs = {}  # (worker, symbol) -> independent programs sharing features
        self.preparing, self.retry = {}, {}
        self.submitted, self.cancelling = set(), {}
        self.recovered_orders = set()
        self.installed_units = {}
        self.evaluations, self.checkpoint_at = {}, 0.0
        self.maintenance_at = 0.0
        self.calendar_day = timezone.localdate()
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='execution-io')
        self.brokers = ThreadPoolExecutor(max_workers=4, thread_name_prefix='execution-broker')

    def send(self, key, message):
        self.inboxes[partition(key, len(self.inboxes))].put(message, timeout=2)

    def install_account(self, key, instrument_ids=()):
        if key in self.accounts:
            return
        state = recover_account(key)
        self.recovered_orders.update(state.orders)
        config = load_configuration(key, instrument_ids=instrument_ids)
        self.send(key, InstallAccount(state, config['contracts'], config['calendars'], config['programs']))
        self.accounts.add(key)
        # Startup refresh is ordered after already accepted user/broker commands.
        enqueue(*key, Kind.REFRESH, {})

    def bootstrap(self):
        from paper_trading.models import PaperTradingSession
        from live_trading.models import TradingSession
        from trading.models import Account
        keys = {(Mode.PAPER, value) for value in PaperTradingSession.objects.exclude(status=Status.STOPPED).values_list('account_id', flat=True)}
        keys.update((Mode.LIVE, value) for value in TradingSession.objects.exclude(status=Status.STOPPED).values_list('broker_credential_id', flat=True))
        keys.update((Mode.TERMINAL, value) for value in Account.objects.values_list('pk', flat=True))
        for key in sorted(keys):
            if key[0] != Mode.TERMINAL and key[0] not in settings.EXECUTION_ENABLED_SCOPES:
                continue
            try:
                self.install_account(key)
            except ValueError:
                # An invalid saved deployment must not stop unrelated accounts.
                # Its next user configuration command can retry preparation.
                logger.exception('Account preparation failed mode=%s account=%s', *key)

    def prepare(self, key):
        if key in self.preparing or not self.programs.get(key):
            return
        self.preparing[key] = self.pool.submit(prepare_symbol, key[1], list(self.programs[key].values()))

    def install_units(self, account, configuration):
        from .models import EvaluationCheckpoint
        from .snapshots import decode
        touched = set()
        desired = set(configuration['programs'])
        for key in self.installed_units.get(account.key, set()) - desired:
            self.send(key, RemoveUnit(key))
            for values in self.programs.values():
                values.pop(key, None)
        self.installed_units[account.key] = desired
        for unit, program in configuration['programs'].items():
            symbol = configuration['contracts'][unit[2]].symbol
            worker = partition(unit, len(self.inboxes))
            key = worker, symbol
            self.programs.setdefault(key, {})[unit] = program
            position = account.positions.get(unit)
            saved = EvaluationCheckpoint.objects.filter(mode=unit[0], session_id=unit[1], instrument_id=unit[2],
                version_id=program.version, position_revision=account.position_revisions.get(unit, 0)).first()
            self.send(unit, InstallUnit(unit, account.key, program, position_view(account, unit),
                account.statuses[unit[1]], {'symbol': symbol, 'peak': position.peak if position else 0,
                'state': decode(saved.state) if saved else None}))
            touched.add(key)
        for key in touched:
            # A version change can arrive during warmup. Discard that old warmup
            # result and prepare the latest set before re-enabling these units.
            if key in self.preparing:
                self.preparing[key].cancel()
                self.retry[key] = 0
            else:
                self.prepare(key)

    def command_payload(self, command):
        key = command.mode, command.account_id
        payload = command.payload
        now = timezone.now()
        if command.kind == Kind.REFRESH:
            config = load_configuration(key)
            if 'terminal_changes' in payload:
                from brokers.models import BrokerChargeProfile
                from common.costs import snapshot_charge_profile
                changes = payload['terminal_changes']
                for name in ('futures_margin_pct', 'short_option_margin_pct'):
                    if name in changes:
                        config['terminal'][name] = Decimal(changes[name])
                if 'charge_profile' in changes:
                    profile = BrokerChargeProfile.objects.get(pk=changes['charge_profile']) if changes['charge_profile'] else None
                    config['terminal']['profile'] = snapshot_charge_profile(profile)
            if 'session_id' in payload:
                session = int(payload['session_id'])
                if 'close_positions' in payload:
                    config['sessions'][session]['close_on_stop'] = payload['close_positions']
                if 'allocation_changes' in payload:
                    config['sessions'][session]['capital'] = Decimal(payload['allocation_changes']['allocated_capital'])
            self.configurations[command.pk] = config
            return config
        if command.kind == Kind.BROKER:
            return {**payload, 'quantity': int(payload['quantity']), 'average': Decimal(payload['average']),
                    'at': datetime.fromisoformat(payload['at']),
                    'updated_at': datetime.fromisoformat(payload['updated_at']) if payload.get('updated_at') else None,
                    'ordered_at': datetime.fromisoformat(payload['ordered_at']) if payload.get('ordered_at') else None}
        if command.kind == Kind.BALANCE:
            return {**payload, 'delta': Decimal(payload['delta'])}
        if command.kind == Kind.FUNDS:
            return {**payload, 'equity': Decimal(payload['equity']), 'available': Decimal(payload['available']),
                    'at': datetime.fromisoformat(payload['at'])}
        if command.kind == Kind.CANCEL:
            return payload
        if command.kind == Kind.SETTLE:
            from instruments.models import Instrument
            from marketdata.calendar import MarketSessionCalendar
            from .preparation import contract_from_instrument
            instrument = Instrument.objects.get(pk=payload['instrument_id'])
            calendar = MarketSessionCalendar.for_instrument(instrument)
            calendar.load_holidays(instrument.expiry_date, instrument.expiry_date)
            return dict(identity=str(command.request_id), contract=contract_from_instrument(instrument),
                calendar=calendar, price=Decimal(payload['settlement_price']), at=now)
        if command.kind in (Kind.ORDER, Kind.AMEND, Kind.PROTECT):
            from instruments.models import Instrument
            from marketdata.calendar import MarketSessionCalendar
            from .preparation import contract_from_instrument
            instrument = Instrument.objects.get(pk=payload['instrument_id'])
            contract = contract_from_instrument(instrument)
            calendar = MarketSessionCalendar.for_instrument(instrument)
            calendar.load_holidays(now.date()-timedelta(days=1), now.date()+timedelta(days=1))
            quote = latest_observation(contract.symbol)
            unit = key[0], payload.get('session_id', key[1]), instrument.pk
            if command.kind == Kind.ORDER:
                kind = payload['order_type']
                order_type = OrderType.STOP_MARKET if kind == TerminalOrderType.STOP else kind
                decimals = {name: Decimal(payload[name]) if payload.get(name) is not None else None
                            for name in ('limit_price', 'trigger_price', 'stop_loss', 'take_profit')}
                intent = Intent(str(command.request_id), key, unit, payload.get('version', 0),
                    payload.get('position_revision', 0), quote['sequence'], now, payload['side'], payload['reason'],
                    quote['reference_price'], intent=payload.get('intent', OrderIntent.ENTRY),
                    quantity=payload['quantity'], order_type=order_type, reduce_only=payload.get('reduce_only', False),
                    manual=key[0] == Mode.TERMINAL, generation=quote['generation'], observed_at=quote['observed_at'], **decimals)
                return dict(intent=intent, contract=contract, calendar=calendar)
            if command.kind == Kind.PROTECT:
                return dict(unit=unit, stop=Decimal(payload['stop']) if payload['stop'] is not None else None,
                    target=Decimal(payload['target']) if payload['target'] is not None else None,
                    at=now, reference_price=quote['reference_price'])
            changes = {name: Decimal(value) if name in ('price', 'trigger', 'stop_loss', 'take_profit') and value is not None else value
                       for name, value in payload['changes'].items()}
            if changes.get('order_type') == TerminalOrderType.STOP:
                changes['order_type'] = OrderType.STOP_MARKET
            return dict(identity=payload['identity'], changes=changes, at=now, **quote)
        raise ValueError(f'Unsupported command {command.kind}.')

    def poll_commands(self):
        # Only the account owner decides whether a command is financially valid.
        # Keep one external command in flight per account so UI actions retain order.
        first = Command.objects.filter(applied_at__isnull=True,
            mode__in=(*settings.EXECUTION_ENABLED_SCOPES, Mode.TERMINAL)).values('mode', 'account_id').annotate(first=Min('id'))
        # Select the head of each account, not a global page dominated by one
        # busy account. Commands remain ordered within their financial owner.
        for command in Command.objects.filter(pk__in=first.values('first')).order_by('id')[:256]:
            key = command.mode, command.account_id
            if key in self.pending:
                continue
            try:
                self.install_account(key, (command.payload['instrument_id'],) if 'instrument_id' in command.payload else ())
                payload = self.command_payload(command)
                self.pending[key] = command.pk
                self.send(key, Control(command.pk, key, command.kind, payload))
            except (ValueError, FileNotFoundError) as exc:
                self.reject(command, str(exc))

    def reject(self, command, error):
        """Rejected admission is visible and never leaves a phantom working order."""
        from .repository import reject_command
        reject_command(command, error)
        logger.warning('Execution command rejected id=%s: %s', command.pk, error)

    def receive(self, message):
        if isinstance(message, Persist):
            result = message.transition
            record = persist_transition(result, command_id=message.command_id)
            self.send(result.account, Committed(result.account, result.revision))
            if message.command_id is not None:
                self.pending.pop(result.account, None)
            if result.account[0] == Mode.LIVE and record is not None:
                order = result.order
                if order.identity not in self.submitted and not order.broker_id and order.status == 'UNKNOWN':
                    # Only a newly accepted intent may be submitted. Recovered
                    # ambiguous orders are reconciled, never blindly retried.
                    if order.identity not in self.recovered_orders:
                        self.submitted.add(order.identity)
                        self.brokers.submit(broker_call, record.pk)
                if (order.cancel_requested and order.broker_id and order.status in ACTIVE_STATUSES
                        and order.identity not in self.cancelling):
                    self.cancelling[order.identity] = (self.brokers.submit(broker_call, record.pk, cancel=True), time.monotonic())
        elif isinstance(message, SaveControl):
            config = self.configurations.pop(message.identity, None)
            if message.error:
                command = Command.objects.get(pk=message.identity)
                self.reject(command, message.error)
            else:
                persist_control(message)
                self.send(message.account.key, Committed(message.account.key, message.account.revision))
                if config is not None:
                    self.install_units(message.account, config)
            self.pending.pop(message.account.key, None)
        elif isinstance(message, PrepareMarket):
            self.prepare((message.worker, message.symbol))
        elif isinstance(message, EvaluationSaved):
            self.evaluations[message.unit] = message
        elif isinstance(message, (UnitFailure, SessionSettled)):
            from paper_trading.models import PaperTradingSession
            from live_trading.models import TradingSession
            mode = message.unit[0] if isinstance(message, UnitFailure) else message.account[0]
            model = PaperTradingSession if mode == Mode.PAPER else TradingSession
            session_id = message.unit[1] if isinstance(message, UnitFailure) else message.session_id
            session = model.objects.get(pk=session_id)
            if isinstance(message, UnitFailure):
                session.status, session.error_message = Status.ERROR, message.error
            else:
                session.status, session.ended_at = Status.STOPPED, timezone.now()
            session.save()
            account_id = session.account_id if mode == Mode.PAPER else session.broker_credential_id
            enqueue(mode, account_id, Kind.REFRESH, {'session_id': session.pk})
        else:
            raise TypeError(f'Unknown execution output {type(message).__name__}')

    def step(self):
        for _ in range(256):
            try:
                self.receive(self.output.get_nowait())
            except Empty:
                break
        now = time.monotonic()
        for identity, (future, started) in tuple(self.cancelling.items()):
            if future.done() and now - started >= 15:
                # A later broker report may retry an outstanding cancellation.
                # Never retry submissions: an ambiguous placement may be real.
                del self.cancelling[identity]
        if now >= self.maintenance_at:
            from .models import AccountCheckpoint
            existing = set(AccountCheckpoint.objects.values_list('mode', 'account_id'))
            for key in self.accounts - existing:
                for unit in self.installed_units.pop(key, set()):
                    self.send(unit, RemoveUnit(unit))
                    self.evaluations.pop(unit, None)
                    for programs in self.programs.values():
                        programs.pop(unit, None)
                self.send(key, RemoveAccount(key))
                self.accounts.remove(key)
            today = timezone.localdate()
            if today != self.calendar_day:
                # Refresh exchange holidays and contract facts off the tick path.
                for key in self.accounts:
                    enqueue(*key, Kind.REFRESH, {})
                self.calendar_day = today
            self.maintenance_at = now + 10
        if self.evaluations and now >= self.checkpoint_at:
            from .repository import persist_evaluations
            persist_evaluations(list(self.evaluations.values()))
            self.evaluations.clear()
            self.checkpoint_at = now + 1
        for key, future in tuple(self.preparing.items()):
            if not future.done():
                continue
            del self.preparing[key]
            if key in self.retry:
                continue
            try:
                prepared = future.result()
                self.inboxes[key[0]].put(prepared, timeout=2)
            except (ValueError, FileNotFoundError):
                self.retry[key] = now + 1
        for key, deadline in tuple(self.retry.items()):
            if now >= deadline and key not in self.preparing:
                del self.retry[key]
                self.prepare(key)

    def run(self, stop, children):
        from common.redis import runtime_redis
        from .models import AccountCheckpoint
        self.recovered_orders = set()
        from .snapshots import decode
        for row in AccountCheckpoint.objects.iterator():
            self.recovered_orders.update(decode(row.state).orders)
        try:
            self.bootstrap()
            deadline = heartbeat = 0
            while not stop.is_set():
                if any(not child.is_alive() for child in children):
                    raise RuntimeError('An execution worker stopped. Stop the group and recover committed accounts.')
                self.step()
                if time.monotonic() >= heartbeat:
                    # Readiness publication is cold I/O in the parent; workers
                    # never use Redis to evaluate a tick or settle a fill.
                    runtime_redis().set('quantnest:execution:workers', len(children), ex=10)
                    heartbeat = time.monotonic() + 2
                if time.monotonic() >= deadline:
                    self.poll_commands()
                    deadline = time.monotonic() + .1
                stop.wait(.002)
        finally:
            stop.set()
            self.pool.shutdown(wait=True, cancel_futures=True)
            self.brokers.shutdown(wait=True, cancel_futures=True)
            runtime_redis().delete('quantnest:execution:workers')
