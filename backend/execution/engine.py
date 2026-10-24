"""Independent session/instrument decisions over prepared scalar inputs.

Every event updates the rule's previous values before group combination. This
keeps crosses correct even when another condition is false or a group short-circuits.
The account owner alone accepts an intent and changes financial state.
"""
import ast
import operator
from dataclasses import dataclass, field, replace
from decimal import Decimal
from math import isfinite, nan
from uuid import NAMESPACE_URL, uuid5

from common.enums import ComparisonOperator, ExecutionSessionStatus, LogicalOperator, OperandType, OrderIntent, RuleType, Side

from .compiler import FeatureGraph, Operand, Program, Rule
from .types import AccountKey, Intent, PositionView, Tick, UnitKey

ARITHMETIC = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}
COMPARISONS = {ComparisonOperator.GREATER: operator.gt, ComparisonOperator.LESS: operator.lt,
    ComparisonOperator.GREATER_EQUAL: operator.ge, ComparisonOperator.LESS_EQUAL: operator.le,
    ComparisonOperator.EQUAL: operator.eq, ComparisonOperator.NOT_EQUAL: operator.ne}


def arithmetic(node: ast.AST, values: dict[str, float]) -> float:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.UnaryOp):
        value = arithmetic(node.operand, values)
        return -value if isinstance(node.op, ast.USub) else value
    return ARITHMETIC[type(node.op)](arithmetic(node.left, values), arithmetic(node.right, values))


@dataclass(slots=True)
class EvaluationUnit:
    key: UnitKey
    account: AccountKey
    program: Program
    position: PositionView = field(default_factory=PositionView)
    status: str = ExecutionSessionStatus.RUNNING
    sequence: int = 0
    generation: int = 0
    pending: str = ''
    peak: float = nan
    risk_distance: float = 0.0
    exit_reason: str = ''
    previous: dict[int, tuple[float, float]] = field(default_factory=dict)
    samples: dict[int, tuple] = field(default_factory=dict)

    def checkpoint(self) -> dict:
        return dict(sequence=self.sequence, generation=self.generation, peak=self.peak if isfinite(self.peak) else None,
            risk_distance=self.risk_distance,
            exit_reason=self.exit_reason,
            previous={str(key): [value if isfinite(value) else None for value in values]
                      for key, values in self.previous.items()}, samples=self.samples)

    def restore(self, saved: dict) -> None:
        self.sequence, self.generation = saved['sequence'], saved['generation']
        self.peak = saved['peak'] if saved['peak'] is not None else nan
        self.risk_distance = saved.get('risk_distance', 0.0)
        self.exit_reason = saved.get('exit_reason', '')
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

    def value(self, operand: Operand, graph: FeatureGraph, tick: Tick) -> float:
        kind, position = operand.kind, self.position
        if operand.feature is not None:
            return graph.features[operand.feature].at(tick.evaluated_at, int(operand.parameters.get('shift', 0)))
        if kind == OperandType.CONSTANT:
            return float(operand.parameters['value'])
        if kind == OperandType.LTP:
            return tick.price
        if kind == OperandType.MATH_EXPRESSION:
            try:
                return arithmetic(operand.expression, {name: self.value(value, graph, tick) for name, value in operand.variables})
            except (ArithmeticError, ValueError):
                return nan
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
            if not self.risk_distance:
                # Freeze risk from inputs available when the position opened.
                # Later ATR/stop changes must not rewrite the initial R multiple.
                initial = replace(tick, event_time=position.opened_at or tick.event_time, closed_at=None, price=entry)
                self.risk_distance = self.program.stop_distance(entry,
                    lambda operand: self.value(operand, graph, initial), position.quantity > 0)
            distance = self.risk_distance
            if distance <= 0:
                raise ValueError('The stop-loss rules did not produce a positive initial risk distance. Review the position before resuming.')
            return points / distance
        raise ValueError(f'Unresolved operand {kind}.')

    def sample(self, operand: Operand, graph: FeatureGraph, tick: Tick) -> tuple:
        """Crosses advance only when one of their actual inputs advances."""
        if operand.kind == OperandType.CONSTANT:
            return ()
        if operand.variables:
            return tuple(self.sample(value, graph, tick) for _, value in operand.variables)
        if operand.tick_sensitive:
            return tick.generation, tick.sequence - (1 if tick.closed_at else 0)
        return (graph.completed_at(operand.timeframe, tick.evaluated_at)[0],)

    def evaluate_rule(self, rule: Rule, graph: FeatureGraph, tick: Tick) -> tuple[float, float, bool, bool]:
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
        return left, right, hit, changed

    def evaluate(self, graph: FeatureGraph, tick: Tick) -> Intent | None:
        if tick.sequence <= self.sequence and tick.generation == self.generation:
            return None
        if self.sequence and self.generation != tick.generation:
            # A reconnect supplies a new prepared history. Do not manufacture
            # a crossing across observations that this unit never received.
            self.previous.clear()
            self.samples.clear()
        self.sequence, self.generation = tick.sequence, tick.generation
        position = self.position
        if position.quantity:
            if position.opened_at is not None and tick.event_time < position.opened_at:
                return None
            self.peak = tick.price if not isfinite(self.peak) else (
                max(self.peak, tick.price) if position.quantity > 0 else min(self.peak, tick.price))
        if not graph.ready(self.program, tick.evaluated_at):
            return None
        applicable = (RuleType.STOP_LOSS, RuleType.TARGET, RuleType.EXIT) if position.quantity else (RuleType.ENTRY,)
        results = {kind: [] for kind in applicable}
        for group in self.program.groups:
            if group.kind not in applicable:
                continue
            hits = []
            changed = False
            for rule in group.rules:
                _, _, hit, eligible = self.evaluate_rule(rule, graph, tick)
                changed = changed or eligible
                hits.append(hit)
            matched = all(hits) if group.operator == LogicalOperator.AND else any(hits)
            results[group.kind].append((matched, changed, group.name))
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
            identity = str(uuid5(NAMESPACE_URL, f'quantnest:{self.key}:{self.program.version}:{position.revision}:{tick.generation}:{tick.sequence}:{kind}'))
            reason = self.exit_reason or f"{kind} group '{next(name for hit, _, name in groups if hit)}' met"
            exiting = bool(position.quantity)
            if exiting:
                # If an entry is only partly filled, keep the exit decision while
                # its remainder is cancelled. A crossing must not be lost.
                self.exit_reason = reason
            side = (Side.SELL if position.quantity > 0 else Side.BUY) if exiting else self.program.entry_side
            self.pending = identity
            return Intent(identity, self.account, self.key, self.program.version, position.revision,
                tick.sequence, tick.evaluated_at, side, reason, Decimal(str(tick.price)),
                intent=OrderIntent.EXIT if exiting else OrderIntent.ENTRY, generation=tick.generation,
                observed_at=tick.event_time)
        return None
