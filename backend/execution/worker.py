"""Persistent CPU worker: ordered observations, fair actors, independent account owners.

No Django models, Redis clients or broker calls are used here. The controller
prepares inputs and persists outputs. A bounded turn prevents one busy symbol or
session from monopolizing a worker; other workers run in separate CPU processes.
"""
from collections import deque
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from queue import Empty
import time

from common.enums import ExecutionCommandType, ExecutionMode, ExecutionSessionStatus, InstrumentType, OrderIntent, OrderType, Side, TerminalOrderType
from marketdata.shared_memory import SharedMemoryManager

from .engine import EvaluationUnit
from .ledger import ACTIVE_STATUSES, acknowledge, apply_fill, available, cancel_order, hold_until_commit, margin, order_transition, position_view
from .market import PreparedSymbol, complete, observe
from .messages import (Committed, Control, InstallAccount, InstallUnit, Persist, PositionUpdate,
    EvaluationSaved, PrepareMarket, RejectedIntent, RemoveAccount, RemoveUnit, SaveControl, SessionSettled, UnitFailure)
from .owner import AccountOwner
from .types import Fill, Intent, Order, Tick, ZERO

ACTOR_BATCH = 8
OBSERVATION_BATCH = 64


def partition(identity: tuple, workers: int) -> int:
    """Stable across interpreter restarts; Python's randomized hash is unsuitable."""
    return int.from_bytes(hashlib.blake2s(repr(tuple(identity)).encode(), digest_size=8).digest(), 'big') % workers


class Worker:
    def __init__(self, index, inboxes, output):
        self.index, self.inboxes, self.output = index, inboxes, output
        self.local = deque()
        self.units, self.owners, self.markets, self.buffers = {}, {}, {}, {}
        self.events, self.read_cursor, self.generations = {}, {}, {}
        self.actors, self.cursors = deque(), {}
        self.reprepare, self.last_tick = set(), {}
        self.waiting = set()
        self.retry_at = 0.0
        self.warming = set()
        self.checkpoint_at = 0.0
        self.recovering = set()
        self.saved_sequences = {}
        self.evaluation_errors = set()

    def send(self, identity, message):
        target = partition(identity, len(self.inboxes))
        if target == self.index:
            self.local.append(message)
        else:
            self.inboxes[target].put(message, timeout=1)

    def subscribe(self, symbol, actor):
        if symbol not in self.buffers:
            try:
                self.buffers[symbol] = SharedMemoryManager(symbol, '1m')
            except FileNotFoundError:
                self.waiting.add((symbol, actor))
                return False
            snapshot = self.buffers[symbol].snapshot(1)
            self.read_cursor[symbol], self.generations[symbol] = snapshot.sequence, snapshot.generation
            self.events[symbol] = deque()
        identity = actor, symbol
        if identity not in self.cursors:
            self.cursors[identity] = self.read_cursor[symbol] * 2
            self.actors.append(identity)
        return True

    def publish(self, owner, result, command_id=None):
        self.output.put(Persist(result, command_id), timeout=1)
        self.send(result.order.unit, PositionUpdate(result.order.unit, position_view(owner.account, result.order.unit)))
        self.finish_stops(owner.account)

    def remove_actor(self, actor):
        self.waiting = {(symbol, value) for symbol, value in self.waiting if value != actor}
        for identity in tuple(self.cursors):
            if identity[0] == actor:
                del self.cursors[identity]
                self.actors.remove(identity)
        for symbol in tuple(self.buffers):
            if not any(sym == symbol for _, sym in self.cursors):
                self.buffers.pop(symbol).close()
                for values in (self.events, self.markets, self.read_cursor, self.generations, self.last_tick):
                    values.pop(symbol, None)
                self.reprepare.discard(symbol)

    def finish_stops(self, state):
        for session, status in tuple(state.statuses.items()):
            if (status == ExecutionSessionStatus.STOPPING and
                    not any(key[1] == session for key in state.positions) and
                    not any(order.unit[1] == session and order.status in ACTIVE_STATUSES for order in state.working.values())):
                state.statuses[session] = ExecutionSessionStatus.STOPPED
                self.output.put(SessionSettled(state.key, session), timeout=1)

    def handle(self, message):
        if isinstance(message, InstallAccount):
            owner = AccountOwner(message.account)
            owner.contracts, owner.calendars, owner.programs = message.contracts, message.calendars, message.programs
            self.owners[message.account.key] = owner
            for contract in message.contracts.values():
                self.subscribe(contract.symbol, ('account', message.account.key))
        elif isinstance(message, InstallUnit):
            if message.status == ExecutionSessionStatus.RUNNING:
                self.evaluation_errors.discard(message.key)
            unit = self.units.get(message.key)
            if unit is None or unit.program.version != message.program.version:
                unit = EvaluationUnit(message.key, message.account, message.program, message.position, message.status)
                self.warming.add(message.key)
                if message.checkpoint.get('state'):
                    unit.restore(message.checkpoint['state'])
                    self.recovering.add(message.key)
            else:
                unit.program = message.program
                unit.status = message.status
                unit.update_position(message.position)
            self.units[message.key] = unit
            symbol = message.checkpoint['symbol']
            if message.position.quantity and message.key not in self.recovering:
                unit.peak = message.checkpoint.get('peak', float(message.position.average))
            self.subscribe(symbol, ('unit', message.key))
            if message.key in self.recovering and symbol in self.buffers:
                self.cursors[(('unit', message.key), symbol)] = unit.sequence
                self.read_cursor[symbol] = min(self.read_cursor[symbol], unit.sequence // 2)
        elif isinstance(message, RemoveUnit):
            self.evaluation_errors.discard(message.unit)
            self.units.pop(message.unit, None)
            self.warming.discard(message.unit)
            self.recovering.discard(message.unit)
            self.saved_sequences.pop(message.unit, None)
            self.remove_actor(('unit', message.unit))
        elif isinstance(message, RemoveAccount):
            self.owners.pop(message.account, None)
            self.remove_actor(('account', message.account))
        elif isinstance(message, PreparedSymbol):
            if message.symbol not in self.buffers:
                return  # Its last deployment was removed while preparation ran.
            # Warmup includes observations up to its captured cursor. Replay only
            # the later retained ticks; never add their volume twice.
            baseline = message.cursor * 2
            for tick in self.events.get(message.symbol, ()):
                if tick.sequence > baseline and tick.closed_at is None:
                    observe(message, tick)
                    message.cursor = tick.sequence // 2
            for identity in self.cursors:
                if identity[0][0] == 'unit' and identity[1] == message.symbol and identity[0][1] not in self.recovering:
                    self.cursors[identity] = max(self.cursors[identity], baseline)
            self.markets[message.symbol] = message
            for (kind, key), symbol in self.actors:
                if kind == 'unit' and symbol == message.symbol and all(
                        feature in message.graph.features for feature in self.units[key].program.features):
                    self.warming.discard(key)
            self.reprepare.discard(message.symbol)
        elif isinstance(message, PositionUpdate):
            if message.unit in self.units:
                self.units[message.unit].update_position(message.position)
        elif isinstance(message, Committed):
            acknowledge(self.owners[message.account].account, message.revision)
        elif isinstance(message, RejectedIntent):
            unit = self.units.get(message.unit)
            if unit is not None and unit.pending == message.identity:
                unit.pending = ''
        elif isinstance(message, Intent):
            owner = self.owners[message.account]
            try:
                if message.intent == OrderIntent.EXIT:
                    entries = [order for order in owner.account.working.values()
                        if order.unit == message.unit and order.intent == OrderIntent.ENTRY and order.status in ACTIVE_STATUSES]
                    for order in entries:
                        if owner.account.live:
                            order.cancel_requested = True
                            result = order_transition(owner.account, order)
                        else:
                            result = cancel_order(owner.account, order.identity, reason='Protective exit requested.')
                        owner.index(order)
                        self.publish(owner, result)
                    if entries:
                        raise ValueError('Cancelling the remaining entry quantity before a full exit.')
                result = owner.accept(message, owner.contracts[message.unit[2]])
                self.publish(owner, result)
            except ValueError as exc:
                self.send(message.unit, RejectedIntent(message.unit, message.identity, str(exc)))
        elif isinstance(message, Control):
            self.control(message)
        else:
            raise TypeError(f'Unknown worker message {type(message).__name__}')

    def control(self, command):
        """External actions enter the same serialized account owner as rule intents."""
        owner = self.owners[command.account]
        state, payload, kind = owner.account, command.payload, command.kind
        try:
            if kind == ExecutionCommandType.ORDER:
                intent = payload['intent']
                if 'contract' in payload:
                    owner.contracts[intent.unit[2]] = payload['contract']
                    owner.calendars[payload['contract'].symbol] = payload['calendar']
                    self.subscribe(payload['contract'].symbol, ('account', command.account))
                if intent.manual:
                    intent = replace(intent, position_revision=position_view(state, intent.unit).revision)
                result = owner.accept(intent, owner.contracts[intent.unit[2]])
                self.publish(owner, result, command.identity)
                return
            if kind == ExecutionCommandType.SETTLE:
                contract, at, price = payload['contract'], payload['at'], payload['price']
                if (state.key[0] != ExecutionMode.TERMINAL or
                    contract.instrument_type not in (InstrumentType.FUTURE, InstrumentType.OPTION) or
                    contract.expiry is None or at < payload['calendar'].session_close(contract.expiry)):
                    raise ValueError('Settlement is available only after derivative contract expiry.')
                if not price.is_finite() or price < ZERO:
                    raise ValueError('Settlement price must be finite and nonnegative.')
                unit = state.key[0], state.key[1], contract.instrument_id
                view = position_view(state, unit)
                if not view.quantity or view.pending:
                    raise ValueError('Finish working orders before settling this position.')
                order = Order(payload['identity'], unit, contract, Side.SELL if view.quantity > 0 else Side.BUY,
                    abs(view.quantity), at, 'MANUAL_SETTLEMENT', intent=OrderIntent.EXIT,
                    order_type=TerminalOrderType.SETTLEMENT, reduce_only=True, manual=True,
                    charge_profile=deepcopy(state.profiles.get(state.key[1], {})), reference_price=price)
                state.orders[order.identity] = order
                try:
                    result = apply_fill(state, Fill(order.identity, order.quantity, price, at))
                except ValueError:
                    del state.orders[order.identity]
                    raise
                self.publish(owner, result, command.identity)
                return
            if kind == ExecutionCommandType.BROKER:
                result = owner.broker_observation(**payload)
                self.publish(owner, result, command.identity)
                return
            if kind == ExecutionCommandType.CANCEL:
                order = state.orders[payload['identity']]
                if state.live and order.status in ACTIVE_STATUSES:
                    order.cancel_requested = True
                    result = order_transition(state, order)
                else:
                    result = cancel_order(state, order.identity)
                if result is not None:
                    owner.index(order)
                    self.publish(owner, result, command.identity)
                    return
            elif kind == ExecutionCommandType.AMEND:
                original = state.orders[payload['identity']]
                if original.status not in ACTIVE_STATUSES or state.live:
                    raise ValueError('Only working simulated orders can be amended here.')
                order = deepcopy(original)
                for key, value in payload['changes'].items():
                    setattr(order, key, value)
                if order.quantity < order.filled:
                    raise ValueError('Quantity cannot be less than the quantity already filled.')
                order.contract.validate(order.quantity, (order.price, order.trigger, order.stop_loss, order.take_profit), payload['at'])
                if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and order.price is None:
                    raise ValueError('A limit price is required.')
                if order.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT) and order.trigger is None:
                    raise ValueError('A trigger price is required.')
                order.eligible_at = payload['at']
                order.sequence, order.generation = payload['sequence'], payload['generation']
                if 'trigger' in payload['changes'] or order.order_type != original.order_type:
                    order.activated_at = None
                old_position = state.positions.get(order.unit)
                quantity = old_position.quantity if old_position else 0
                already_closing = sum(other.remaining for other in state.working.values()
                    if other.identity != order.identity and other.unit == order.unit and
                    other.side == order.side and other.status in ACTIVE_STATUSES)
                reducing = (min(max(abs(quantity) - already_closing, 0), order.remaining)
                            if (quantity > 0) != (order.side == Side.BUY) else 0)
                if order.reduce_only and reducing < order.remaining:
                    raise ValueError('Existing orders already reserve this position for closing.')
                price = order.price or order.trigger or payload['reference_price']
                order.reserved = margin(state, order.contract,
                    (order.remaining-reducing) * (1 if order.side == Side.BUY else -1), price)
                if order.reserved > available(state, order.unit[1]) + original.reserved:
                    raise ValueError('Insufficient capital for the amended order.')
                state.orders[order.identity] = order
                owner.index(order)
                self.publish(owner, order_transition(state, order), command.identity)
                return
            elif kind == ExecutionCommandType.PROTECT:
                position = state.positions[payload['unit']]
                stop, target = payload['stop'], payload['target']
                position.contract.validate(abs(position.quantity), (stop, target), payload['at'])
                reference, long = payload['reference_price'], position.quantity > 0
                if stop is not None and (stop >= reference if long else stop <= reference):
                    raise ValueError('Place the stop on the protective side of the current price.')
                if target is not None and (target <= reference if long else target >= reference):
                    raise ValueError('Place the target beyond the current price.')
                position.stop_loss, position.take_profit = stop, target
                position.revision += 1
                state.position_revisions[position.unit] = position.revision
            elif kind == ExecutionCommandType.BALANCE:
                delta = payload['delta']
                if delta < 0 and -delta > available(state, payload['session_id']):
                    raise ValueError('Capital is committed to positions or pending orders.')
                state.balance += delta
                hold_until_commit(state, state.revision + 1, delta)
            elif kind == ExecutionCommandType.FUNDS:
                if state.broker_observed_at is None or payload['at'] >= state.broker_observed_at:
                    state.balance, state.broker_available = payload['equity'], payload['available']
                    state.broker_observed_at = payload['at']
                    # A snapshot was requested at this committed revision. Retain
                    # spending after it: a concurrent fill may not be in the reply.
                    state.broker_spending = {revision: amount for revision, amount in state.broker_spending.items()
                                            if revision > payload['revision']}
            elif kind == ExecutionCommandType.REFRESH:
                for session, config in payload['sessions'].items():
                    missing = [key for key in state.positions if key[1] == session and key not in payload['programs']]
                    if missing:
                        raise ValueError('The selected version must retain instruments with open positions.')
                    if config['capital'] is not None:
                        # Apply only a principal delta. Concurrent realized P&L
                        # belongs to this owner and cannot be reset by a DB read.
                        current = state.allocation_principal.get(session, config['capital'])
                        delta = config['capital'] - current
                        if delta < 0 and -delta > available(state, session):
                            raise ValueError('Capital is committed to positions or working orders.')
                if 'terminal' in payload:
                    candidate = deepcopy(state)
                    config = payload['terminal']
                    candidate.profiles[state.key[1]] = config['profile']
                    candidate.futures_margin_pct = config['futures_margin_pct']
                    candidate.short_option_margin_pct = config['short_option_margin_pct']
                    for position in candidate.positions.values():
                        position.margin = margin(candidate, position.contract, position.quantity, position.average)
                    # Working orders retain their original margin settings until
                    # they settle. Changing margin with orders open is ambiguous.
                    if any(o.status in ACTIVE_STATUSES for o in candidate.working.values()):
                        if (state.futures_margin_pct != candidate.futures_margin_pct or
                                state.short_option_margin_pct != candidate.short_option_margin_pct):
                            raise ValueError('Finish working orders before changing margin settings.')
                    if sum((p.margin for p in candidate.positions.values()), ZERO) > candidate.balance:
                        raise ValueError('The selected margin settings exceed available capital.')
                    state.profiles = candidate.profiles
                    state.futures_margin_pct, state.short_option_margin_pct = candidate.futures_margin_pct, candidate.short_option_margin_pct
                    for key, position in candidate.positions.items():
                        state.positions[key].margin = position.margin
                for session, config in payload['sessions'].items():
                    state.versions[session], state.statuses[session] = config['version'], config['status']
                    state.profiles[session], state.slippage[session] = config['profile'], config['slippage']
                    if config['capital'] is not None:
                        previous = state.allocation_principal.get(session, config['capital'])
                        state.allocations[session] = state.allocations.get(session, config['capital']) + config['capital'] - previous
                        state.allocation_principal[session] = config['capital']
                    state.sizing.update(config['sizing'])
                    state.close_on_stop[session] = config['close_on_stop']
                owner.programs.update(payload['programs'])
                owner.contracts.update(payload['contracts'])
                owner.calendars.update(payload['calendars'])
                for contract in payload['contracts'].values():
                    self.subscribe(contract.symbol, ('account', command.account))
                for order in tuple(state.working.values()):
                    if (not order.manual and order.intent == OrderIntent.ENTRY and order.status in ACTIVE_STATUSES and
                        (state.statuses[order.unit[1]] != ExecutionSessionStatus.RUNNING or
                         state.versions[order.unit[1]] != order.version)):
                        if state.live:
                            order.cancel_requested = True
                            result = order_transition(state, order)
                        else:
                            result = cancel_order(state, order.identity, reason='Session configuration changed.')
                        owner.index(order)
                        self.publish(owner, result)
            else:
                raise ValueError(f'Unsupported control action {kind}.')
            state.revision += 1
            self.output.put(SaveControl(command.identity, deepcopy(state)), timeout=1)
            self.finish_stops(state)
        except (ValueError, KeyError) as exc:
            self.output.put(SaveControl(command.identity, deepcopy(state), str(exc)), timeout=1)

    def read_market(self, symbol):
        buffer = self.buffers[symbol]
        rows, lost, revision, generation = buffer.read_observations(self.read_cursor[symbol], OBSERVATION_BATCH)
        prepared = self.markets.get(symbol)
        changed = prepared is not None and revision != prepared.revisions['1m']
        if lost or generation != self.generations[symbol] or changed:
            if symbol not in self.reprepare:
                self.reprepare.add(symbol)
                self.output.put(PrepareMarket(self.index, symbol,
                    'Observed tick buffer was overwritten.' if lost else 'Market history or connection changed.'), timeout=1)
            self.generations[symbol] = generation
            if lost:
                for (kind, key), sym in self.actors:
                    if kind == 'unit' and sym == symbol:
                        self.units[key].status = ExecutionSessionStatus.ERROR
                        self.output.put(UnitFailure(key, 'Observed ticks were lost; review and resume the session.'), timeout=1)
        events = self.events[symbol]
        for sequence, event, received, price, volume in rows:
            tick = Tick(symbol, int(sequence)*2, datetime.fromtimestamp(event, timezone.utc), received, price, volume, generation)
            if prepared is not None and symbol not in self.reprepare and int(sequence) > prepared.cursor:
                observe(prepared, tick)
                prepared.cursor = int(sequence)
            events.append(tick)
            self.last_tick[symbol] = tick
            self.read_cursor[symbol] = int(sequence)
        now = datetime.now(timezone.utc)
        last = self.last_tick.get(symbol)
        if (prepared is not None and symbol not in self.reprepare and complete(prepared, now)
                and last is not None and last.generation == generation):
            # Odd sequence numbers represent candle-clock events between provider ticks.
            events.append(replace(last, sequence=last.sequence+1, closed_at=now, volume=0))

    def actor_turn(self):
        if not self.actors:
            return False
        actor, symbol = self.actors.popleft()
        identity = actor, symbol
        self.actors.append(identity)
        cursor = self.cursors[identity]
        ready = [tick for tick in self.events[symbol] if tick.sequence > cursor][:ACTOR_BATCH]
        kind, key = actor
        for tick in ready:
            if kind == 'account':
                if tick.closed_at is None:
                    owner = self.owners[key]
                    results, more = owner.observe(tick)
                    for result in results:
                        self.publish(owner, result)
                    if more:
                        return True  # Continue this same observation on the next fair turn.
            else:
                prepared = self.markets.get(symbol)
                if prepared is None or symbol in self.reprepare or key in self.warming:
                    return False
                unit = self.units[key]
                if key in self.evaluation_errors:
                    self.cursors[identity] = tick.sequence
                    continue
                try:
                    intent = unit.evaluate(prepared.graph, tick)
                except (ValueError, ArithmeticError) as exc:
                    self.evaluation_errors.add(key)
                    unit.status = ExecutionSessionStatus.ERROR
                    self.output.put(UnitFailure(key, str(exc)), timeout=1)
                    self.cursors[identity] = tick.sequence
                    continue
                if intent is not None:
                    self.send(unit.account, intent)
            self.cursors[identity] = tick.sequence
            if kind == 'unit' and self.cursors[identity] >= self.markets[symbol].cursor * 2:
                self.recovering.discard(key)
        return bool(ready)

    def step(self):
        for _ in range(128):
            try:
                message = self.local.popleft() if self.local else self.inboxes[self.index].get_nowait()
            except Empty:
                break
            self.handle(message)
        if time.monotonic() >= self.retry_at:
            self.retry_at = time.monotonic() + 1
            for symbol, actor in tuple(self.waiting):
                if self.subscribe(symbol, actor):
                    self.waiting.remove((symbol, actor))
        for symbol in self.buffers:
            cursors = [cursor for (_, sym), cursor in self.cursors.items() if sym == symbol]
            minimum = min(cursors, default=self.read_cursor[symbol]*2)
            while self.events[symbol] and self.events[symbol][0].sequence <= minimum:
                self.events[symbol].popleft()
            # Backpressure leaves unconsumed events in the provider ring. A real
            # overflow is explicit, rather than silently replacing ticks with LTP.
            if len(self.events[symbol]) < 256:
                self.read_market(symbol)
        busy = False
        for _ in range(len(self.actors)):
            busy = self.actor_turn() or busy
        if time.monotonic() >= self.checkpoint_at:
            self.checkpoint_at = time.monotonic() + 5
            for key, unit in self.units.items():
                stamp = unit.generation, unit.sequence, unit.position.revision, unit.program.version
                if (unit.sequence and stamp != self.saved_sequences.get(key) and not unit.pending
                        and not unit.position.pending and key not in self.warming):
                    self.output.put(EvaluationSaved(key, unit.account, unit.program.version,
                        unit.position.revision, unit.checkpoint()), timeout=1)
                    self.saved_sequences[key] = stamp
        return busy or bool(self.local)

    def close(self):
        for buffer in self.buffers.values():
            buffer.close()


def run_worker(index, inboxes, output, stop):
    worker = Worker(index, inboxes, output)
    try:
        while not stop.is_set():
            if not worker.step():
                stop.wait(.002)
    finally:
        worker.close()
