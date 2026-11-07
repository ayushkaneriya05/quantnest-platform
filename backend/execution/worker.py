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
from itertools import islice
from queue import Empty
import time

from common.enums import ExecutionCommandType, ExecutionMode, ExecutionSessionStatus, OrderIntent, OrderType, Side
from marketdata.shared_memory import SharedMemoryManager

from .engine import EvaluationUnit
from .compiler import CandleHistoryConflict
from .ledger import ACTIVE_STATUSES, acknowledge, available, hold_until_commit, margin, order_transition, position_view
from .market import PreparedSymbol, complete, observe
from .messages import (Committed, Control, InstallAccount, InstallUnit, Persist, PositionUpdate,
    EvaluationSaved, PrepareMarket, RejectedIntent, RemoveAccount, RemoveUnit, SaveControl, SaveSettlement, SessionSettled, UnitFailure)
from .owner import AccountOwner
from .types import Intent, Tick, ZERO

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
        self.graphs = {}
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
        self.unit_sources = {}

    def send(self, identity, message):
        target = partition(identity, len(self.inboxes))
        if target == self.index:
            self.local.append(message)
        else:
            self.inboxes[target].put(message, timeout=1)

    def prepare_market(self, symbol):
        """Pause only this symbol's evaluators while the controller rebuilds it."""
        if symbol not in self.reprepare:
            self.reprepare.add(symbol)
            self.graphs.pop(symbol, None)
            self.output.put(PrepareMarket(self.index, symbol), timeout=1)

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
            self.cursors[identity] = (self.read_cursor[symbol] * 2, 0.0)
            self.actors.append(identity)
        return True

    def publish(self, owner, result, command_id=None):
        # Automatic routes preload candidate features in evaluator workers, but
        # account matching only needs contracts with admitted exposure/orders.
        self.subscribe(result.order.contract.symbol, ('account', owner.account.key))
        self.output.put(Persist(result, command_id), timeout=1)
        self.send(result.order.unit, PositionUpdate(result.order.unit, position_view(owner.account, result.order.unit)))
        self.finish_stops(owner.account)

    def remove_actor(self, actor, keep=()):
        """Release obsolete subscriptions; preserve cursors for retained inputs."""
        self.waiting = {(symbol, value) for symbol, value in self.waiting if value != actor or symbol in keep}
        for identity in tuple(self.cursors):
            if identity[0] == actor and identity[1] not in keep:
                del self.cursors[identity]
                self.actors.remove(identity)
        for symbol in tuple(self.buffers):
            if not any(sym == symbol for _, sym in self.cursors):
                self.buffers.pop(symbol).close()
                for values in (self.events, self.markets, self.graphs, self.read_cursor, self.generations, self.last_tick):
                    values.pop(symbol, None)
                self.reprepare.discard(symbol)

    def finish_stops(self, state):
        for session, status in tuple(state.statuses.items()):
            if (status == ExecutionSessionStatus.STOPPING and
                    not any(key[1] == session for key in state.positions) and
                    not any(order.unit[1] == session for order in state.working.values())):
                state.statuses[session] = ExecutionSessionStatus.STOPPED
                self.output.put(SessionSettled(state.key, session), timeout=1)

    def subscribe_account(self, owner):
        """Cold refresh retains exposure; unselected candidates need no matcher."""
        identities = ({program.binding[1] for program in owner.programs.values() if program.selection is None}
                      if owner.account.key[0] != ExecutionMode.TERMINAL else set(owner.contracts))
        identities.update(position.contract.instrument_id for position in owner.account.positions.values())
        identities.update(order.contract.instrument_id for order in owner.account.working.values())
        for identity in identities:
            self.subscribe(owner.contracts[identity].symbol, ('account', owner.account.key))

    def handle(self, message):
        if isinstance(message, InstallAccount):
            owner = AccountOwner(message.account)
            owner.contracts, owner.calendars, owner.programs = message.contracts, message.calendars, message.programs
            self.owners[message.account.key] = owner
            self.subscribe_account(owner)
        elif isinstance(message, InstallUnit):
            if message.status == ExecutionSessionStatus.RUNNING:
                self.evaluation_errors.discard(message.key)
            unit = self.units.get(message.key)
            replace_unit = unit is None or unit.program.version != message.program.version
            if replace_unit:
                unit = EvaluationUnit(message.key, message.account, message.program, message.position, message.status)
                self.warming.add(message.key)
                if message.checkpoint.get('state'):
                    unit.restore(message.checkpoint['state'])
                    self.recovering.add(message.key)
            else:
                # Capital/session refreshes must not retarget a selected contract
                # or erase an armed setup whose strategy version is unchanged.
                binding = unit.program.binding
                unit.program = (replace(message.program, binding=binding)
                    if message.program.selection is not None and message.program.permits_binding(binding)
                    else message.program)
                if message.status != unit.status and message.status != ExecutionSessionStatus.RUNNING:
                    unit.reset_observations()
                unit.status = message.status
                unit.update_position(message.position)
            self.units[message.key] = unit
            symbol = message.checkpoint['symbol']
            sources = message.checkpoint['bindings']
            old_sources = self.unit_sources.get(message.key)
            if old_sources and old_sources != sources and unit.program.selection is not None and not replace_unit:
                # Catalog refresh adds/removes candidates without replaying the
                # unaffected streams or discarding underlying-only setup state.
                actor = ('unit', message.key)
                self.remove_actor(actor, keep=set(sources.values()))
                for source in set(old_sources.values()) - set(sources.values()):
                    unit.route_quotes.pop(source, None)
            elif old_sources and old_sources != sources:
                self.remove_actor(('unit', message.key))
                unit.reset_observations()
                unit.source_quotes.clear()
                unit.source_cursors.clear()
                unit.source_clocks.clear()
            self.unit_sources[message.key] = sources
            if message.position.quantity and message.key not in self.recovering:
                unit.peak = message.checkpoint.get('peak', float(message.position.average))
            for source in set(sources.values()):
                self.subscribe(source, ('unit', message.key))
            if unit.program.selection is not None:
                # Financial binding is authoritative; fresh candidate observations
                # repopulate quotes after startup without replaying stale prices.
                if replace_unit:
                    unit.source_quotes.clear()
                    unit.source_cursors.clear()
                    unit.source_clocks.clear()
                    unit.route_quotes.clear()
                    unit.reset_observations()
                self.recovering.discard(message.key)
                return
            if sources['signal'] != sources['trade']:
                # Each stream has its own saved cursor. Quotes are rebuilt from
                # observed ticks; a saved LTP is never treated as a new event.
                for role, source in sources.items():
                    cursor = unit.source_cursors.get(role)
                    if message.key in self.recovering and source in self.buffers and cursor:
                        if cursor[0] == self.generations[source]:
                            self.cursors[(('unit', message.key), source)] = (cursor[1], unit.source_clocks.get(role, 0.0))
                            self.read_cursor[source] = min(self.read_cursor[source], cursor[1] // 2)
                        else:
                            unit.reset_observations()
                            unit.source_quotes.pop(role, None)
                            unit.source_cursors.pop(role, None)
                            unit.source_clocks.pop(role, None)
                return
            if message.key in self.recovering and symbol in self.buffers:
                if unit.generation == self.generations[symbol]:
                    self.cursors[(('unit', message.key), symbol)] = (unit.sequence, unit.clock)
                    self.read_cursor[symbol] = min(self.read_cursor[symbol], unit.sequence // 2)
                else:
                    # Sequence numbers belong to one feed generation. A restart
                    # must not rewind the new feed using an old checkpoint.
                    unit.reset_observations()
                    unit.sequence = self.read_cursor[symbol] * 2
                    unit.generation = self.generations[symbol]
                    unit.clock = 0.0
                    self.recovering.discard(message.key)
        elif isinstance(message, RemoveUnit):
            self.evaluation_errors.discard(message.unit)
            self.units.pop(message.unit, None)
            self.unit_sources.pop(message.unit, None)
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
            try:
                for tick in self.events.get(message.symbol, ()):
                    if tick.sequence > baseline and tick.closed_at is None:
                        observe(message, tick)
                        message.cursor = tick.sequence // 2
            except CandleHistoryConflict:
                # A delayed tick can also arrive during preparation. Request a
                # newer snapshot instead of installing a partially replayed graph.
                self.reprepare.discard(message.symbol)
                self.prepare_market(message.symbol)
                return
            for identity in self.cursors:
                if identity[0][0] == 'unit' and identity[1] == message.symbol and identity[0][1] not in self.recovering:
                    self.cursors[identity] = max(self.cursors[identity], (baseline, 0.0))
            self.markets[message.symbol] = message
            self.graphs[message.symbol] = message.graph
            for (kind, key), symbol in self.actors:
                if kind == 'unit' and symbol == message.symbol:
                    sources = self.unit_sources[key]
                    program = self.units[key].program
                    if program.selection is not None:
                        self.warming.discard(key)
                        continue  # Per-selected-contract readiness is checked at evaluation.
                    if all(source in self.markets and all(feature in self.markets[source].graph.features
                        for feature in (program.features if sources['signal'] == sources['trade'] else program.market_inputs[role][2]))
                        for role, source in sources.items()):
                        self.warming.discard(key)
            self.reprepare.discard(message.symbol)
        elif isinstance(message, PositionUpdate):
            if message.unit in self.units:
                self.units[message.unit].update_position(message.position)
        elif isinstance(message, Committed):
            acknowledge(self.owners[message.account].account, message.revision)
        elif isinstance(message, RejectedIntent):
            unit = self.units.get(message.unit)
            if unit is not None:
                unit.reject_intent(message.identity)
        elif isinstance(message, Intent):
            owner = self.owners[message.account]
            try:
                if message.intent == OrderIntent.EXIT:
                    entries = [order for order in owner.account.working.values()
                        if order.unit == message.unit and order.intent == OrderIntent.ENTRY]
                    for order in entries:
                        result = owner.cancel(order.identity, reason='Protective exit requested.')
                        self.publish(owner, result)
                    if entries:
                        raise ValueError('Cancelling the remaining entry quantity before a full exit.')
                result = owner.accept(message, owner.contracts[message.binding[1]])
                self.publish(owner, result)
            except ValueError:
                self.send(message.unit, RejectedIntent(message.unit, message.identity))
        elif isinstance(message, Control):
            self.control(message)
        else:
            raise TypeError(f'Unknown worker message {type(message).__name__}')

    def control(self, command):
        """External actions enter the same serialized account owner as rule intents."""
        owner = self.owners[command.account]
        state, payload, kind = owner.account, command.payload, command.kind
        try:
            if kind == ExecutionCommandType.SETTLEMENT:
                from .settlements import apply_settlement
                result = apply_settlement(state, **payload)
                self.output.put(SaveSettlement(command.identity, deepcopy(state), result), timeout=1)
                unit = payload['unit']
                self.send(unit, PositionUpdate(unit, position_view(state, unit)))
                self.finish_stops(state)
                return
            if kind == ExecutionCommandType.ORDER:
                intent = payload['intent']
                if 'contract' in payload:
                    owner.contracts[payload['contract'].instrument_id] = payload['contract']
                    owner.calendars[payload['contract'].symbol] = payload['calendar']
                    self.subscribe(payload['contract'].symbol, ('account', command.account))
                if intent.manual:
                    intent = replace(intent, position_revision=position_view(state, intent.unit).revision)
                result = owner.accept(intent, owner.contracts[intent.binding[1]])
                self.publish(owner, result, command.identity)
                return
            if kind == ExecutionCommandType.BROKER:
                result = owner.broker_observation(**payload)
                self.publish(owner, result, command.identity)
                return
            if kind == ExecutionCommandType.CANCEL:
                result = owner.cancel(payload['identity'], reason=payload.get('reason', ''))
                if result is not None:
                    self.publish(owner, result, command.identity)
                    return
            elif kind == ExecutionCommandType.AMEND:
                original = state.orders[payload['identity']]
                if original.status not in ACTIVE_STATUSES or state.live:
                    raise ValueError('Only working simulated orders can be amended here.')
                order = deepcopy(original)
                for key, value in payload['changes'].items():
                    setattr(order, key, value)
                if order.quantity <= order.filled:
                    raise ValueError('Quantity must exceed the quantity already filled. Cancel the remaining order instead.')
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
                    other.side == order.side)
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
                position = state.positions.get(payload['unit'])
                if position is None:
                    raise ValueError('This position has already closed. Refresh the positions list.')
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
                    if config['version'] != state.versions.get(session):
                        for key, position in state.positions.items():
                            if key[1] != session:
                                continue
                            program = payload['programs'][key]
                            # The committed position owns its source binding,
                            # including after a restart or a late broker fill.
                            if not program.permits_binding(position.binding):
                                raise ValueError('Close positions before changing their signal or traded instrument.')
                            if program.initial_risk is not None and position.stop_distance <= 0:
                                raise ValueError('This position has no frozen initial risk. Close it before deploying a version with an explicit risk basis.')
                            if position.setup_state or any(group.setup for group in program.groups):
                                raise ValueError('Close positions before changing a version that uses captured setup values.')
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
                    if candidate.working and (state.futures_margin_pct != candidate.futures_margin_pct or
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
                owner.programs = payload['programs']
                # Keep facts for orders that filled after this configuration was
                # read, including late broker fills from a previous version.
                owner.contracts.update(payload['contracts'])
                owner.calendars.update(payload['calendars'])
                self.subscribe_account(owner)
                for order in tuple(state.working.values()):
                    if (not order.manual and order.intent == OrderIntent.ENTRY and
                        (state.statuses[order.unit[1]] != ExecutionSessionStatus.RUNNING or
                         state.versions[order.unit[1]] != order.version)):
                        result = owner.cancel(order.identity, reason='Session configuration changed.')
                        self.publish(owner, result)
            else:
                raise ValueError(f'Unsupported control action {kind}.')
            state.revision += 1
            self.output.put(SaveControl(command.identity, deepcopy(state)), timeout=1)
            self.finish_stops(state)
        except (ValueError, KeyError) as exc:
            if kind == ExecutionCommandType.BROKER and payload.get('quantity', 0) > 0:
                order = state.orders.get(payload.get('identity'))
                if order is not None:
                    state.statuses[order.unit[1]] = ExecutionSessionStatus.ERROR
                    self.output.put(UnitFailure(order.unit, str(exc), state.versions.get(order.unit[1], order.version)), timeout=1)
            self.output.put(SaveControl(command.identity, deepcopy(state), str(exc)), timeout=1)

    def read_market(self, symbol):
        buffer = self.buffers[symbol]
        rows, lost, revision, generation = buffer.read_observations(self.read_cursor[symbol], OBSERVATION_BATCH)
        prepared = self.markets.get(symbol)
        changed = prepared is not None and revision != prepared.revisions['1m']
        generation_changed = generation != self.generations[symbol]
        if lost or generation_changed or changed:
            self.prepare_market(symbol)
            self.generations[symbol] = generation
            for (kind, key), sym in self.actors:
                if kind != 'unit' or sym != symbol:
                    continue
                unit = self.units[key]
                if unit.program.selection is not None:
                    unit.route_quotes.pop(symbol, None)
                    active = (self.unit_sources[key]['signal'], unit.program.candidates[unit.program.binding[1]])
                    if symbol not in active:
                        continue  # An unused candidate cannot invalidate this route's signal state.
                unit.reset_observations()
                if generation_changed:
                    unit.route_quotes.pop(symbol, None)
                    for role, source in self.unit_sources[key].items():
                        if source == symbol:
                            unit.source_quotes.pop(role, None)
                            unit.source_cursors.pop(role, None)
                            unit.source_clocks.pop(role, None)
                # Reconnect/history repair can recover automatically. Lost
                # observations still require review; their signals are unknown.
                if lost:
                    unit.status = ExecutionSessionStatus.ERROR
                    self.output.put(UnitFailure(key, 'Observed ticks were lost; review and resume the session.', unit.program.version), timeout=1)
        events = self.events[symbol]
        for sequence, event, _, price, volume in rows:
            # Normalize transport scalars once before they enter the numerical
            # kernel; price/volume must not retain NumPy scalar types from SHM.
            tick = Tick(symbol, int(sequence)*2, datetime.fromtimestamp(event, timezone.utc),
                        float(price), float(volume), generation)
            if prepared is not None and symbol not in self.reprepare and int(sequence) > prepared.cursor:
                try:
                    observe(prepared, tick)
                    prepared.cursor = int(sequence)
                except CandleHistoryConflict:
                    self.prepare_market(symbol)
            events.append(tick)
            self.last_tick[symbol] = tick
            self.read_cursor[symbol] = int(sequence)
        now = datetime.now(timezone.utc)
        last = self.last_tick.get(symbol)
        # A full batch may leave older ticks unread. Drain them before advancing
        # to wall-clock time, otherwise ordinary backlog looks like late history.
        if prepared is not None and symbol not in self.reprepare and len(rows) < OBSERVATION_BATCH:
            try:
                if complete(prepared, now) and last is not None and last.generation == generation:
                    # Odd sequence numbers represent candle-clock events between provider ticks.
                    # Use the actual boundary, not the poll time a few ms later:
                    # provider timestamps have whole-second precision, so a
                    # 14:20:00 quote must remain eligible for a 14:20 close.
                    closed_at = max(prepared.graph.completed.values())
                    events.append(replace(last, sequence=last.sequence+1, closed_at=closed_at, volume=0))
            except CandleHistoryConflict:
                self.prepare_market(symbol)

    def actor_turn(self):
        if not self.actors:
            return False
        actor, symbol = self.actors.popleft()
        identity = actor, symbol
        self.actors.append(identity)
        cursor = self.cursors[identity]
        ready = list(islice((tick for tick in self.events[symbol] if tick.cursor > cursor), ACTOR_BATCH))
        if not ready:
            return False  # Idle candidates need no cross-stream merge scan.
        kind, key = actor
        if kind == 'unit':
            # A route consumes its inputs in event-time order. Actor fairness
            # must not let a newer option quote hide an older index crossing.
            # This merge is local to the route; unrelated sessions never wait.
            other_times = []
            for source in set(self.unit_sources[key].values()) - {symbol}:
                other_cursor = self.cursors.get((actor, source), (0, 0.0))
                next_tick = next((item for item in self.events.get(source, ())
                                  if item.cursor > other_cursor), None)
                if next_tick is not None:
                    other_times.append(next_tick.evaluated_at)
            if other_times:
                boundary = min(other_times)
                ready = [item for item in ready if item.evaluated_at <= boundary]
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
                unit = self.units[key]
                if unit.program.selection is None and not unit.position.quantity and (prepared is None or symbol in self.reprepare or key in self.warming):
                    return False
                if key in self.evaluation_errors:
                    self.cursors[identity] = tick.cursor
                    continue
                try:
                    sources = self.unit_sources[key]
                    if unit.program.selection is not None:
                        intent = unit.evaluate_selected(self.graphs, tick, sources['signal'])
                    elif sources['signal'] == sources['trade']:
                        graph = prepared.graph if prepared is not None and symbol not in self.reprepare else None
                        intent = unit.evaluate(graph, tick)
                    else:
                        graphs = {role: self.markets[source].graph for role, source in sources.items()
                                  if source in self.markets and source not in self.reprepare}
                        if not unit.position.quantity and len(graphs) != len(sources):
                            return False
                        role = next(role for role, source in sources.items() if source == symbol)
                        intent = unit.evaluate_sources(graphs, tick, role)
                except (ValueError, ArithmeticError) as exc:
                    self.evaluation_errors.add(key)
                    unit.status = ExecutionSessionStatus.ERROR
                    self.output.put(UnitFailure(key, str(exc), self.units[key].program.version), timeout=1)
                    self.cursors[identity] = tick.cursor
                    continue
                if intent is not None:
                    self.send(unit.account, intent)
            self.cursors[identity] = tick.cursor
            if kind == 'unit' and key in self.recovering and all(source in self.markets and
                    self.cursors[(actor, source)][0] >= self.markets[source].cursor * 2
                    for source in set(self.unit_sources[key].values())):
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
        # One pass across consumers, instead of scanning every session for each
        # symbol. Retain ticks until the slowest subscribed actor has read them.
        minimums = {}
        for (_, symbol), cursor in self.cursors.items():
            minimums[symbol] = min(minimums.get(symbol, cursor), cursor)
        for symbol in self.buffers:
            minimum = minimums.get(symbol, (self.read_cursor[symbol]*2, 0.0))
            while self.events[symbol] and self.events[symbol][0].cursor <= minimum:
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
                stamp = unit.generation, unit.sequence, unit.clock, unit.position.revision, unit.program.version
                if (unit.sequence and stamp != self.saved_sequences.get(key) and not unit.pending
                        and not unit.position.pending and key not in self.warming):
                    self.output.put(EvaluationSaved(key, unit.program.version,
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
