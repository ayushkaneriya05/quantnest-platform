"""Independent session/instrument decisions over prepared scalar inputs.

Every event updates the rule's previous values before group combination. This
keeps crosses correct even when another condition is false or a group short-circuits.
The account owner alone accepts an intent and changes financial state.
"""
import operator
from copy import deepcopy
from dataclasses import dataclass, field, replace
from decimal import Decimal
from math import isfinite, nan
from uuid import NAMESPACE_URL, uuid5

from common.enums import ComparisonOperator, ExecutionSessionStatus, LogicalOperator, OperandType, OrderIntent, RuleType, Side

from .compiler import FeatureGraph, Operand, Program, Rule
from .expressions import boolean_result
from .types import AccountKey, Intent, PositionView, Tick, UnitKey

COMPARISONS = {ComparisonOperator.GREATER: operator.gt, ComparisonOperator.LESS: operator.lt,
    ComparisonOperator.GREATER_EQUAL: operator.ge, ComparisonOperator.LESS_EQUAL: operator.le,
    ComparisonOperator.EQUAL: operator.eq, ComparisonOperator.NOT_EQUAL: operator.ne}


@dataclass(slots=True)
class EvaluationUnit:
    key: UnitKey
    account: AccountKey
    program: Program
    position: PositionView = field(default_factory=PositionView)
    status: str = ExecutionSessionStatus.RUNNING
    sequence: int = 0
    generation: int = 0
    clock: float = 0.0
    pending: str = ''
    peak: float = nan
    risk_distance: float = 0.0
    exit_reason: str = ''
    previous: dict[int, tuple[float, float]] = field(default_factory=dict)
    samples: dict[int, tuple] = field(default_factory=dict)
    setups: dict[str, dict] = field(default_factory=dict)
    source_cursors: dict = field(default_factory=dict)
    source_clocks: dict = field(default_factory=dict)
    source_quotes: dict = field(default_factory=dict)
    source_graphs: dict = field(default_factory=dict)
    expression_values: dict = field(default_factory=dict)
    expression_samples: dict = field(default_factory=dict)
    route_quotes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._restore_owned_setup()

    def _restore_owned_setup(self) -> None:
        # Financial ownership is the recovery authority after an accepted order.
        # Evaluator checkpoints may predate its fill or belong to an old version.
        for identity, saved in self.position.setup_state.items():
            self.setups[identity] = {**deepcopy(saved),
                'phase': 'owned' if self.position.quantity else 'fired'}

    def checkpoint(self) -> dict:
        return dict(sequence=self.sequence, generation=self.generation, clock=self.clock, binding=self.program.binding,
            peak=self.peak if isfinite(self.peak) else None,
            risk_distance=self.risk_distance,
            exit_reason=self.exit_reason,
            setups=deepcopy(self.setups),
            source_cursors=dict(self.source_cursors),
            source_clocks=dict(self.source_clocks),
            source_quotes={role: dict(symbol=quote.symbol, sequence=quote.sequence,
                event_time=quote.event_time, price=quote.price, generation=quote.generation)
                for role, quote in self.source_quotes.items()},
            previous={str(key): [value if isfinite(value) else None for value in values]
                      for key, values in self.previous.items()}, samples=self.samples)

    def restore(self, saved: dict) -> None:
        if self.program.selection is not None and self.program.permits_binding(saved.get('binding')):
            self.program = replace(self.program, binding=saved['binding'])
        self.sequence, self.generation = saved['sequence'], saved['generation']
        self.clock = saved.get('clock', 0.0)
        self.source_cursors = dict(saved.get('source_cursors', {}))
        self.source_clocks = dict(saved.get('source_clocks', {}))
        self.source_quotes = {role: Tick(**quote) for role, quote in saved.get('source_quotes', {}).items()}
        self.peak = saved['peak'] if saved['peak'] is not None else nan
        self.risk_distance = saved.get('risk_distance', 0.0)
        self.exit_reason = saved.get('exit_reason', '')
        self.setups = deepcopy(saved.get('setups', {}))
        for identity, state in self.setups.items():
            if state['phase'] in ('fired', 'owned') and identity not in self.position.setup_state:
                # A decision checkpoint can arrive before financial admission.
                # Never restore its uncommitted occurrence as an owned trade.
                state.update(phase='idle', captures={}, arm_seen=True)
        self._restore_owned_setup()
        self.previous = {int(key): tuple(nan if item is None else item for item in values)
                         for key, values in saved['previous'].items()}
        # Source stamps contain datetimes and nested tuples and use the same
        # explicit JSON codec as financial snapshots.
        self.samples = {int(key): value for key, value in saved['samples'].items()}

    def update_position(self, position: PositionView) -> None:
        if position.revision < self.position.revision:
            return
        if position.revision != self.position.revision:
            # Today's position values must never be broadcast across yesterday's
            # candles to manufacture a historical crossing.
            self.previous.clear()
            self.samples.clear()
            if not self.position.quantity or self.position.quantity * position.quantity <= 0:
                self.peak = float(position.average) if position.quantity else nan
                self.risk_distance = 0.0
                self.exit_reason = ''
        self.position = position
        self.pending = ''
        self._restore_owned_setup()
        for state in self.setups.values():
            if position.quantity and state['phase'] == 'fired':
                state['phase'] = 'owned'
            elif position.quantity and state['phase'] == 'armed':
                state.update(phase='idle', captures={})
            elif not position.quantity and not position.pending and state['phase'] in ('fired', 'owned'):
                state.update(phase='idle', captures={})

    def reject_intent(self, identity: str) -> None:
        if self.pending == identity:
            self.pending = ''
            if not self.position.quantity and not self.position.pending:
                for state in self.setups.values():
                    if state['phase'] == 'fired':
                        state.update(phase='idle', captures={})

    def reset_observations(self) -> None:
        """Discard unproven sequences after a gap; keep captures protecting exposure."""
        self.previous.clear()
        self.samples.clear()
        for state in self.setups.values():
            if state['phase'] not in ('fired', 'owned'):
                state.update(phase='idle', captures={}, arm_seen=True)

    def value(self, operand: Operand, graph: FeatureGraph | None, tick: Tick) -> float:
        kind, position = operand.kind, self.position
        if operand.capture is not None:
            setup, name = operand.capture
            return self.setups.get(setup, {}).get('captures', {}).get(name, nan)
        if self.source_cursors:
            graph = self.source_graphs.get(operand.source)
        if operand.feature is not None:
            feature = graph.features.get(operand.feature) if graph is not None else None
            return feature.at(tick.evaluated_at, int(operand.parameters.get('shift', 0))) if feature is not None else nan
        if kind == OperandType.CONSTANT:
            return float(operand.parameters['value'])
        if kind == OperandType.LTP:
            observed = self.source_quotes.get(operand.source) if self.source_cursors else tick
            return observed.price if observed is not None and observed.event_time <= tick.evaluated_at else nan
        if kind == OperandType.MATH_EXPRESSION:
            name = operand.expression_name
            if name and name in self.expression_values:
                return self.expression_values[name]
            result = operand.calculation.evaluate(self.value(value, graph, tick) for _, value in operand.variables)
            if name:
                self.expression_values[name] = result
            return result
        if not position.quantity:
            return nan
        entry = float(position.average)
        points = (tick.price - entry) * (1 if position.quantity > 0 else -1)
        if kind == OperandType.ENTRY_PRICE:
            return entry
        if kind == OperandType.POSITION_PNL_POINTS:
            return points
        if kind == OperandType.POSITION_PNL_PERCENTAGE:
            return 100 * points / entry if entry else nan
        if kind == OperandType.TRAILING_PEAK_OFFSET:
            return self.peak - tick.price if position.quantity > 0 else tick.price - self.peak
        if kind == OperandType.POSITION_RR_RATIO:
            if position.stop_distance > 0:
                return points / position.stop_distance
            if self.program.initial_risk is not None:
                # An older open position cannot acquire a newly edited risk
                # denominator. Its entry admission owns that immutable value.
                return nan
            if not self.risk_distance:
                # Freeze risk from inputs available when the position opened.
                # Later ATR/stop changes must not rewrite the initial R multiple.
                initial = replace(tick, event_time=position.opened_at or tick.event_time, closed_at=None, price=entry)
                self.risk_distance = self.program.stop_distance(entry,
                    lambda operand: self.value(operand, graph, initial), position.quantity > 0)
            distance = self.risk_distance
            if distance <= 0:
                # A gap can fill an entry beyond its inferred stop. R is then
                # undefined, but the matching stop/other exits must still run.
                return nan
            return points / distance
        raise ValueError(f'Unresolved operand {kind}.')

    def sample(self, operand: Operand, graph: FeatureGraph | None, tick: Tick) -> tuple:
        """Crosses advance only when one of their actual inputs advances."""
        if operand.capture is not None:
            return (self.setups.get(operand.capture[0], {}).get('armed_at'),)
        if operand.kind == OperandType.CONSTANT:
            return ()
        if operand.variables:
            name = operand.expression_name
            if name and name in self.expression_samples:
                return self.expression_samples[name]
            result = tuple(self.sample(value, graph, tick) for _, value in operand.variables)
            if name:
                self.expression_samples[name] = result
            return result
        if self.source_cursors:
            graph = self.source_graphs.get(operand.source)
        if operand.tick_sensitive:
            observed = self.source_quotes.get(operand.source) if self.source_cursors else tick
            return (observed.generation, observed.sequence - (1 if observed.closed_at else 0)) if observed is not None else (None,)
        return (graph.completed_at(operand.timeframe, tick.evaluated_at)[0] if graph is not None else None,)

    def evaluate_rule(self, rule: Rule, graph: FeatureGraph | None, tick: Tick) -> tuple[float, float, bool, bool]:
        """Resolve values and advance crossing state once per input observation.

        Research calls this same operation without creating trading intents.
        Returns left value, right value, match and whether the inputs advanced.
        """
        left, right = self.value(rule.left, graph, tick), self.value(rule.right, graph, tick)
        prior = self.previous.get(rule.identity)
        stamp = self.sample(rule.left, graph, tick), self.sample(rule.right, graph, tick)
        changed = self.samples.get(rule.identity) != stamp
        hit = False
        if isfinite(left) and isfinite(right):
            if rule.comparison in COMPARISONS:
                hit = COMPARISONS[rule.comparison](left, right)
            elif changed and prior is not None and all(isfinite(value) for value in prior):
                hit = (left > right and prior[0] <= prior[1] if rule.comparison == ComparisonOperator.CROSSES_ABOVE
                       else left < right and prior[0] >= prior[1])
        if changed:
            self.previous[rule.identity] = left, right
            self.samples[rule.identity] = stamp
        # SHM observations can carry NumPy scalars. Their comparisons produce
        # numpy.bool_, which is truthy but is not Python's True singleton used
        # by the three-valued condition evaluator. Publish one Boolean type.
        return left, right, bool(hit), changed

    def condition(self, group, graph, tick):
        """Advance every comparison before combining; UNKNOWN is retained."""
        hits, changed = [], False
        for rule in group.rules:
            prior = self.previous.get(rule.identity)
            left, right, hit, eligible = self.evaluate_rule(rule, graph, tick)
            changed = changed or eligible
            if (not (isfinite(left) and isfinite(right)) or
                    rule.comparison not in COMPARISONS and
                    (prior is None or not all(isfinite(value) for value in prior))):
                hit = None
            hits.append(hit)
        matched = boolean_result(group.conditions, hits)
        return matched, changed

    def setup_condition(self, group, graph, tick):
        """One occurrence per arming edge; at most one phase advances per event.

        Captures are written only when armed. They survive fills/checkpoints for
        protection and are cleared when flat, invalidated, expired or unproven.
        """
        setup = group.setup
        state = self.setups.setdefault(setup.identity, dict(phase='idle', arm_seen=False, captures={}))
        arm, advanced = self.condition(setup.arm, graph, tick)
        edge = arm is True and advanced and not state['arm_seen']
        if advanced and arm is not None:
            state['arm_seen'] = arm is True
        if state['phase'] in ('fired', 'owned'):
            return False, False
        if self.pending or self.position.pending or self.status != ExecutionSessionStatus.RUNNING or not self.program.allows_entry(tick.evaluated_at):
            state.update(phase='idle', captures={})
            return False, False
        if state['phase'] == 'idle':
            if edge:
                captured = {name: self.value(value, graph, tick) for name, value in setup.captures}
                if not all(isfinite(value) for value in captured.values()):
                    return False, False
                state.update(phase='armed', captures=captured, armed_at=tick.evaluated_at,
                             last_bar=graph.completed_at(setup.timeframe, tick.evaluated_at)[0], bars=0, step=0)
                # Seed confirmation crosses against the newly frozen values.
                # The arming observation itself cannot confirm or trade.
                for part in (*setup.steps, group):
                    for rule in part.rules:
                        self.previous.pop(rule.identity, None)
                        self.samples.pop(rule.identity, None)
                    self.condition(part, graph, tick)
            return False, False
        closed = graph.completed_at(setup.timeframe, tick.evaluated_at)[0]
        if closed is not None and closed != state['last_bar']:
            state['bars'] += sum(1 for at, _ in graph.completions.get(setup.timeframe, ())
                                 if (state['last_bar'] is None or at > state['last_bar']) and at <= tick.evaluated_at)
            state['last_bar'] = closed
        invalid = self.condition(setup.invalidate, graph, tick)[0] if setup.invalidate else False
        # Update all stateful comparisons even when another step is waiting.
        steps = [self.condition(part, graph, tick) for part in setup.steps]
        trigger = self.condition(group, graph, tick)
        if state['bars'] >= setup.expires_after_bars or invalid is True:
            state.update(phase='idle', captures={})
            return False, False
        if invalid is None:
            return False, False
        if state['step'] < len(steps):
            hit, changed = steps[state['step']]
            if hit is True and changed:
                state['step'] += 1
            return False, False
        return trigger

    def evaluate_sources(self, graphs: dict[str, FeatureGraph], event: Tick, role: str) -> Intent | None:
        """Join received source observations without borrowing a future quote.

        Each source retains its own cursor. A decision uses only the quotes this
        actor has consumed; its fill reference and matching cursor always belong
        to the traded contract, never the underlying signal market.
        """
        previous = self.source_cursors.get(role)
        if previous is not None and previous[0] == event.generation and event.cursor <= (previous[1], self.source_clocks.get(role, 0.0)):
            return None
        if previous is not None and previous[0] != event.generation:
            self.reset_observations()
        self.source_cursors[role] = event.generation, event.sequence
        self.source_clocks[role] = event.cursor[1]
        if event.closed_at is None:
            self.source_quotes[role] = event
        trade = self.source_quotes.get('trade')
        if trade is None or trade.event_time > event.evaluated_at:
            return None
        # Network delivery can reorder exchange timestamps across connections.
        # Keep the observation but do not evaluate an impossible joined state.
        if not self.position.quantity:
            if (set(self.source_quotes) != {'signal', 'trade'} or
                    any(quote.event_time > event.evaluated_at for quote in self.source_quotes.values())):
                return None
            if not all(source in graphs and all(graphs[source].completed_at(tf, event.evaluated_at)[1] >= count
                       for tf, count in requirements[0].items())
                       for source, requirements in self.program.market_inputs.items()):
                return None
        # Open exposure can use ready protective inputs while another history
        # graph rebuilds. Missing inputs stay UNKNOWN, never borrowed by role.
        self.source_graphs = graphs
        joined = replace(event, sequence=self.sequence + 1, generation=0, price=trade.price)
        intent = self.evaluate(graphs.get('signal'), joined)
        return replace(intent, sequence=trade.sequence, generation=trade.generation) if intent is not None else None

    def evaluate_selected(self, graphs: dict, event: Tick, signal_symbol: str) -> Intent | None:
        """Resolve a prepared route in memory and pin it for the owned cycle.

        Candidate quotes arrive through the same ordered actor inputs as the
        signal. Selection never reads a latest-price HTTP/cache endpoint. A
        missing selected graph/quote waits; it never substitutes another strike.
        """
        if event.closed_at is None:
            self.route_quotes[event.symbol] = event
        signal = self.route_quotes.get(signal_symbol)
        pinned = self.position.binding if self.position.pending or self.position.quantity else None
        if pinned is None and self.pending:
            pinned = self.program.binding
        if pinned is None:
            if signal is None or signal.event_time > event.evaluated_at:
                return None
            try:
                selected = self.program.selection.select(Decimal(str(signal.price)),
                    event.evaluated_at.astimezone(self.program.calendar.zone).date())
            except ValueError:
                return None  # No eligible contract: keep consuming the signal clock.
            pinned = self.program.binding[0], selected.instrument_id
        if not self.program.permits_binding(pinned):
            raise ValueError('Owned contract is absent from this prepared route.')
        if pinned != self.program.binding:
            # Crosses/captures from one premium series cannot continue on another.
            for identity in self.program.rebind_rules:
                self.previous.pop(identity, None)
                self.samples.pop(identity, None)
            for identity in self.program.rebind_setups:
                state = self.setups.get(identity)
                if state and state['phase'] not in ('fired', 'owned'):
                    state.update(phase='idle', captures={}, arm_seen=True)
            self.source_cursors.clear()
            self.source_clocks.clear()
            self.source_quotes.clear()
            self.program = replace(self.program, binding=pinned)
        trade_symbol = self.program.candidates[pinned[1]]
        if event.symbol not in (signal_symbol, trade_symbol):
            return None
        for role, symbol in (('signal', signal_symbol), ('trade', trade_symbol)):
            quote = self.route_quotes.get(symbol)
            if quote is not None and quote.event_time <= event.evaluated_at:
                self.source_quotes[role] = quote
        selected_graphs = {role: graphs[symbol] for role, symbol in
            (('signal', signal_symbol), ('trade', trade_symbol)) if symbol in graphs}
        return self.evaluate_sources(selected_graphs, event,
            'signal' if event.symbol == signal_symbol else 'trade')

    def evaluate(self, graph: FeatureGraph | None, tick: Tick) -> Intent | None:
        if tick.cursor <= (self.sequence, self.clock) and tick.generation == self.generation:
            return None
        if self.sequence and self.generation != tick.generation:
            # A reconnect supplies a new prepared history. Do not manufacture
            # a crossing across observations that this unit never received.
            self.reset_observations()
        self.sequence, self.generation = tick.sequence, tick.generation
        self.clock = tick.cursor[1]
        # Pure named formulas share work only inside this observation. A later
        # tick/bar/source event always sees its own values, including UNKNOWN.
        self.expression_values.clear()
        self.expression_samples.clear()
        position = self.position
        if position.quantity:
            if position.opened_at is not None and tick.event_time < position.opened_at:
                return None
            self.peak = tick.price if not isfinite(self.peak) else (
                max(self.peak, tick.price) if position.quantity > 0 else min(self.peak, tick.price))
        if not position.quantity:
            if self.status != ExecutionSessionStatus.RUNNING:
                return None  # Pausing a flat session must not arm hidden setups.
            if not self.source_cursors and (graph is None or not graph.ready(self.program, tick.evaluated_at)):
                return None
        applicable = (RuleType.STOP_LOSS, RuleType.TARGET, RuleType.EXIT) if position.quantity else (RuleType.ENTRY,)
        results = {kind: [] for kind in applicable}
        for group in self.program.groups:
            if group.kind not in applicable:
                continue
            matched, changed = (self.setup_condition(group, graph, tick) if group.setup else self.condition(group, graph, tick))
            results[group.kind].append((matched is True, changed, group.name))
        if self.pending or position.pending and (not position.quantity or self.exit_reason):
            return None
        if not position.quantity and (self.status != ExecutionSessionStatus.RUNNING or not self.program.allows_entry(tick.evaluated_at)):
            return None
        for kind in applicable:
            groups = results[kind]
            if not groups:
                continue
            matched = all(hit for hit, _, _ in groups) if self.program.group_operators[kind] == LogicalOperator.AND else any(hit for hit, _, _ in groups)
            if not self.exit_reason and (not matched or not any(changed for _, changed, _ in groups)):
                continue
            initial_risk = 0.0
            if not position.quantity and self.program.initial_risk is not None:
                initial_risk = self.value(self.program.initial_risk, graph, tick)
                if not isfinite(initial_risk) or initial_risk <= 0:
                    return None  # No entry on an unavailable/zero risk basis.
            identity = str(uuid5(NAMESPACE_URL, f'quantnest:{self.key}:{self.program.version}:{position.revision}:{tick.generation}:{tick.sequence}:{self.clock}:{kind}'))
            reason = self.exit_reason or f"{kind} group '{next(name for hit, _, name in groups if hit)}' met"
            exiting = bool(position.quantity)
            if exiting:
                # If an entry is only partly filled, keep the exit decision while
                # its remainder is cancelled. A crossing must not be lost.
                self.exit_reason = reason
            side = (Side.SELL if position.quantity > 0 else Side.BUY) if exiting else self.program.entry_side
            self.pending = identity
            if not exiting:
                # A rejected/cancelled occurrence requires a new arming edge;
                # a partial fill retains captures until its full position closes.
                for group in self.program.groups:
                    if group.setup:
                        state = self.setups.get(group.setup.identity)
                        if state and state['phase'] == 'armed':
                            state['phase'] = 'fired'
            return Intent(identity, self.account, self.key, self.program.version, position.revision,
                tick.sequence, tick.evaluated_at, side, reason, Decimal(str(tick.price)),
                intent=OrderIntent.EXIT if exiting else OrderIntent.ENTRY, generation=tick.generation,
                initial_risk_distance=initial_risk,
                binding=self.program.binding,
                setup_state={key: deepcopy(state) for key, state in self.setups.items()
                             if state['phase'] == 'fired'} if not exiting else {})
        return None
