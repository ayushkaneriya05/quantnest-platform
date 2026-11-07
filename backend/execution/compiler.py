"""Compile immutable strategy snapshots once, outside the market-event loop."""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, time
from functools import partial
from math import ceil, isfinite
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from common.enums import CandleTimeframe, ComparisonOperator, LogicalOperator, OperandType, RuleType, Side
from strategies.specification.operands import INDICATOR_OPERANDS, POSITION_OPERANDS, get_operand_parameter_config, get_operand_parameter_defaults
from marketdata.contracts import interval_minutes, source_timeframe

from .features import Feature, RollingFeature
from .expressions import (
    Calculation, compile_arithmetic, compile_condition, compile_numeric,
    input_requirements, parse_arithmetic_expression, validate_tree,
)
from .types import Candle

if TYPE_CHECKING:
    from instruments.selection import PreparedSelector
    from marketdata.calendar import MarketSessionCalendar

FeatureKey = tuple[str, str, str]
PRICE_SOURCES = frozenset((OperandType.OPEN, OperandType.HIGH, OperandType.LOW, OperandType.CLOSE,
                          OperandType.VOLUME, OperandType.HL2, OperandType.HLC3, OperandType.OHLC4))
MIN_WARMUP_BARS = 20
RECURSIVE_WARMUP_PERIODS = 5


def _indicator_warmup(kind: str, params: dict) -> int:
    """Preserve the numerical warmup policy, including recursive convergence."""
    period = int(params.get('period', 14))
    if kind == OperandType.MACD:
        return (int(params['slow_period']) + int(params['signal_period'])) * RECURSIVE_WARMUP_PERIODS
    if kind == OperandType.STOCHASTIC:
        return int(params['k_period']) + int(params['d_period']) + int(params['smooth'])
    if kind == OperandType.ICHIMOKU_CLOUD:
        return max(int(params['tenkan']), int(params['kijun']), int(params['senkou'])) + int(params['kijun'])
    if kind == OperandType.HMA:
        return period + ceil(period ** 0.5)
    if kind in {OperandType.EMA, OperandType.KAMA, OperandType.DEMA, OperandType.TEMA,
                OperandType.RSI, OperandType.SUPERTREND, OperandType.ADX, OperandType.DMI,
                OperandType.ATR, OperandType.KELTNER_CHANNEL}:
        return period * RECURSIVE_WARMUP_PERIODS
    return MIN_WARMUP_BARS if kind == OperandType.CANDLE_PATTERN else max(period, MIN_WARMUP_BARS)


def _operand_warmup(kind: str, params: dict, timeframe: str, calendar) -> int:
    params = {**get_operand_parameter_defaults(kind), **params}
    lookback = _indicator_warmup(kind, params) if kind in INDICATOR_OPERANDS else MIN_WARMUP_BARS
    # Session/week operands retain their full anchor period, including boundaries.
    week = len(calendar.trading_weekdays)
    sessions = (2 * week if kind in {OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW} else
                {'D': 1, 'W': week, 'M': 5 * week}[params['anchor']] if kind == OperandType.VWAP else
                1 if kind == OperandType.CURRENT_DAY_OPEN else 0)
    if sessions:
        minutes = interval_minutes(timeframe)
        anchored = ceil(calendar.session_minutes / minutes) * sessions if minutes else sessions
        lookback = max(lookback, anchored + 2)
    source = params.get('source')
    if source in INDICATOR_OPERANDS:
        lookback += _operand_warmup(source, params.get('source_params', {}), timeframe, calendar) - 1
    return lookback + int(params.get('shift', 0)) + 1  # Preceding observation for crosses.


def strategy_requirements(config: dict, calendar, *, role=None) -> tuple[str, dict, dict]:
    """One history plan for admission, data warmup, research and compilation."""
    base = CandleTimeframe(config['time_rule']['candle_timeframe'])
    counts = {base: MIN_WARMUP_BARS}

    def include(kind, params, timeframe, extra=0):
        timeframe = CandleTimeframe(timeframe)
        if kind == OperandType.CONSTANT:
            return
        if kind == OperandType.MATH_EXPRESSION:
            for variable in params['expression']['variables'].values():
                include(variable['type'], variable.get('params', {}), variable.get('timeframe') or timeframe, extra)
            return
        counts[timeframe] = max(counts.get(timeframe, 0), _operand_warmup(kind, params, timeframe, calendar) + extra)

    for group in config.get('rule_groups', []):
        if not group.get('is_active', True):
            continue
        trees = [group['condition']]
        setup = group.get('setup')
        if setup:
            trees += [setup['arm'], *setup['steps'], *setup['captures'].values()]
            if setup.get('invalidate'):
                trees.append(setup['invalidate'])
            counts.setdefault(CandleTimeframe(setup['timeframe']), MIN_WARMUP_BARS)
        for tree in trees:
            for item, extra in input_requirements(tree, config.get('expressions', {})):
                source = 'trade' if item['type'] in POSITION_OPERANDS else item.get('source', 'signal')
                if role is None or source == role:
                    include(item['type'], item['params'], item.get('timeframe') or base, extra)
    if config.get('initial_risk') is not None:
        for item, extra in input_requirements(config['initial_risk'], config.get('expressions', {})):
            if role is None or role == item.get('source', 'signal'):
                include(item['type'], item['params'], item.get('timeframe') or base, extra)
    sources = {}
    for tf, count in counts.items():
        source = source_timeframe(tf)
        width = interval_minutes(tf) or (7 if tf == CandleTimeframe.W1 else 1)
        sources[source] = max(sources.get(source, 0), (count + 2) * width)
    if CandleTimeframe.D1 in sources:
        sources[CandleTimeframe.M1] = max(sources.get(CandleTimeframe.M1, 0), calendar.session_minutes + 2)
    return base, counts, sources


def source_windows(timeframes, depths, calendar, start, end):
    families = {source_timeframe(tf) for tf in timeframes}
    return {source: (calendar.warmup_start(start, depths[source], source=source,
                    include_weekly=source == CandleTimeframe.D1 and CandleTimeframe.W1 in timeframes), end)
            for source in families}


def normalize_parameters(kind: str, values: dict) -> dict:
    """Use the builder's parameter schema for all numerical paths."""
    result = {**get_operand_parameter_defaults(kind), **values}
    for spec in get_operand_parameter_config(kind):
        key = spec['key']
        if key not in result:
            continue
        value = result[key]
        if spec['type'] == 'number':
            if isinstance(value, bool):
                raise ValueError(f'{kind}.{key} must be numeric.')
            number = float(value)
            integral = float(spec.get('step', 1)).is_integer()
            if (not isfinite(number) or integral and not number.is_integer() or
                spec.get('min') is not None and number < spec['min'] or
                spec.get('max') is not None and number > spec['max']):
                raise ValueError(f'{kind}.{key} is outside its supported range.')
            result[key] = int(number) if integral else number
        elif spec['type'] in ('source', 'select') and value not in {item['value'] for item in spec.get('options', [])}:
            raise ValueError(f'{kind}.{key} is not a supported choice.')
    if kind == OperandType.MACD and result['fast_period'] >= result['slow_period']:
        raise ValueError('MACD fast period must be smaller than its slow period.')
    return result


@dataclass(frozen=True, slots=True)
class Operand:
    kind: str
    timeframe: str
    parameters: dict
    feature: FeatureKey | None = None
    variables: tuple[tuple[str, 'Operand'], ...] = ()
    tick_sensitive: bool = False
    calculation: Calculation | None = None
    capture: tuple[str, str] | None = None
    source: str = 'signal'
    expression_name: str = ''
    window: tuple[str, int, int] | None = None  # operation, bars, variance ddof


@dataclass(frozen=True, slots=True)
class Rule:
    identity: int
    left: Operand
    comparison: str
    right: Operand


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    kind: str
    rules: tuple[Rule, ...]
    tick_sensitive: bool
    conditions: tuple = ()
    setup: 'Setup | None' = None


@dataclass(frozen=True, slots=True)
class Setup:
    identity: str
    arm: Group
    invalidate: Group | None
    steps: tuple[Group, ...]
    captures: tuple[tuple[str, Operand], ...]
    timeframe: str
    expires_after_bars: int


@dataclass(frozen=True, slots=True)
class Program:
    version: int
    base_timeframe: str
    counts: dict[str, int]
    sources: dict[str, int]
    groups: tuple[Group, ...]
    group_operators: dict[str, str]
    features: dict[FeatureKey, Operand]
    entry_side: str
    calendar: MarketSessionCalendar
    zone: ZoneInfo
    trading_days: frozenset[str]
    start: time | None
    end: time | None
    no_trade_windows: tuple[tuple[time, time], ...]
    market_inputs: dict = field(default_factory=dict)
    binding: tuple[int, int] | None = None
    market_calendars: dict = field(default_factory=dict)
    initial_risk: Operand | None = None
    selection: PreparedSelector | None = None
    candidates: dict[int, str] = field(default_factory=dict)
    rebind_rules: frozenset[int] = frozenset()
    rebind_setups: frozenset[str] = frozenset()

    def permits_binding(self, binding):
        return (binding == self.binding if self.selection is None else
                binding is not None and binding[0] == self.binding[0] and binding[1] in self.candidates)

    def for_source(self, role):
        """Cold projection: prepare only features required from this market."""
        from dataclasses import replace
        counts, sources, features = self.market_inputs[role]
        return replace(self, counts=counts, sources=sources, features=features,
                       calendar=self.market_calendars[role], market_inputs={}, selection=None, candidates={})

    def for_live(self):
        """Live ticks/position values need subscriptions, not historical bars.

        Replay still needs base candles to synthesize observations. Only the
        live preparation boundary removes a source's unused candle warmup.
        A setup keeps its signal clock so capture expiry can count bars.
        """
        from dataclasses import replace
        setup_clock = any(group.setup is not None for group in self.groups)
        inputs = {role: values if values[2] or (role == 'signal' and setup_clock) else ({}, {}, {})
                  for role, values in self.market_inputs.items()}
        counts, sources = {}, {}
        for history, acquisition, _ in inputs.values():
            for target, requirements in ((counts, history), (sources, acquisition)):
                for timeframe, depth in requirements.items():
                    target[timeframe] = max(target.get(timeframe, 0), depth)
        return replace(self, counts=counts, sources=sources, market_inputs=inputs)

    def stop_distance(self, entry: float, resolve, long: bool) -> float:
        """Risk/reward needs an actual unconditional stop, never an invented 1%."""
        distances = []
        groups = [group for group in self.groups if group.kind == RuleType.STOP_LOSS]
        for group in groups:
            values = []
            for rule in group.rules:
                if rule.left.kind in (OperandType.POSITION_PNL_POINTS, OperandType.POSITION_PNL_PERCENTAGE):
                    value = resolve(rule.right)
                    if rule.comparison not in (ComparisonOperator.LESS, ComparisonOperator.LESS_EQUAL) or value >= 0:
                        return 0.0
                    distance = -value if rule.left.kind == OperandType.POSITION_PNL_POINTS else entry * -value / 100
                elif rule.left.kind in (OperandType.LTP, OperandType.CLOSE):
                    expected = (ComparisonOperator.LESS, ComparisonOperator.LESS_EQUAL) if long else (ComparisonOperator.GREATER, ComparisonOperator.GREATER_EQUAL)
                    if rule.comparison not in expected:
                        return 0.0
                    distance = (entry - resolve(rule.right)) * (1 if long else -1)
                else:
                    return 0.0
                if not isfinite(distance) or distance <= 0:
                    return 0.0
                values.append(distance)
            # Monotone stop trees have a deterministic first breach distance.
            # NOT / threshold voting need an explicit initial_risk expression.
            slots = []
            for op, children, _ in group.conditions:
                if op == 'rule':
                    slots.append(values[children[0]])
                elif op in ('all', 'any'):
                    slots.append((max if op == 'all' else min)(slots[i] for i in children))
                else:
                    return 0.0
            if slots:
                distances.append(slots[-1])
        return ((max if self.group_operators[RuleType.STOP_LOSS] == LogicalOperator.AND else min)(distances)
                if distances else 0.0)

    def allows_entry(self, at: datetime) -> bool:
        local = at.astimezone(self.zone)
        clock = local.time()
        return (self.calendar.is_open(at) and
            (not self.trading_days or local.strftime('%A') in self.trading_days) and
            (self.start is None or clock >= self.start) and (self.end is None or clock <= self.end) and
            not any(left <= clock <= right for left, right in self.no_trade_windows))


def compile_strategy(config: dict, version: int, *, calendar, signal_calendar=None) -> Program:
    base, counts, sources = strategy_requirements(config, calendar)
    features = {}
    market_features = {'signal': {}, 'trade': {}}

    def operand(kind: str, params: dict, timeframe: str, source='signal') -> Operand:
        kind = OperandType(kind)
        timeframe = CandleTimeframe(timeframe or base)
        parameters = normalize_parameters(kind, params)
        if kind == OperandType.MATH_EXPRESSION:
            formula = parameters['expression']
            expression = parse_arithmetic_expression(formula['expression'], formula['variables'])
            variables = tuple((name, operand(spec['type'], spec.get('params', {}), spec.get('timeframe') or timeframe, source))
                              for name, spec in formula['variables'].items())
            return Operand(kind, timeframe, parameters, variables=variables,
                           tick_sensitive=any(value.tick_sensitive for _, value in variables),
                           calculation=compile_arithmetic(expression, formula['variables']), source=source)
        if kind in POSITION_OPERANDS or kind == OperandType.LTP:
            if parameters.get('shift', 0):
                raise ValueError('Tick and position operands do not support candle shifts; use CLOSE for historical prices.')
            return Operand(kind, timeframe, parameters, tick_sensitive=True,
                           source='trade' if kind in POSITION_OPERANDS else source)
        if kind == OperandType.CONSTANT:
            return Operand(kind, timeframe, parameters)
        # Shift belongs to the reader, not the indicator. Two shifts reuse one node.
        numerical = {key: value for key, value in parameters.items() if key != 'shift'}
        key = kind, timeframe, json.dumps(numerical, sort_keys=True, separators=(',', ':'))
        result = Operand(kind, timeframe, parameters, feature=key, source=source)
        features[key] = result
        market_features[source][key] = result
        return result

    groups, identity = [], 0
    expressions = config.get('expressions', {})
    named_operands = {}

    def named(name):
        if name not in named_operands:
            value = compile_numeric(expressions[name], operand, named, window)
            # A single shared operand preserves the formula's own source clocks.
            # Its value and sample are cached per observation by EvaluationUnit.
            named_operands[name] = Operand(OperandType.MATH_EXPRESSION, '', {},
                variables=((name, value),), tick_sensitive=value.tick_sensitive,
                calculation=Calculation((), 0), expression_name=name)
        return named_operands[name]

    def window(node):
        child = compile_numeric(node['args'][0], operand, named, window)
        clocks = set()

        def signature(value):
            if value.capture or value.tick_sensitive:
                raise ValueError('Rolling formulas require completed candles, not ticks, positions or captured values.')
            if value.feature is not None:
                clocks.add((value.source, value.timeframe))
            operations = tuple((function.__name__ if function else None, indexes)
                               for function, indexes in value.calculation.instructions) if value.calculation else ()
            return (value.kind, value.timeframe, value.parameters, value.window, operations,
                    value.calculation.result if value.calculation else None,
                    tuple(signature(item) for _, item in value.variables))

        identity = signature(child)
        if len(clocks) != 1:
            raise ValueError('Each rolling formula needs one market source and one candle timeframe. Combine different windows outside the rolling formula.')
        source, timeframe = next(iter(clocks))
        ddof = node.get('ddof', 0)
        key = f'window:{node["op"]}', timeframe, json.dumps((node['bars'], ddof, identity), sort_keys=True, separators=(',', ':'))
        result = Operand(OperandType.MATH_EXPRESSION, timeframe, {}, feature=key,
                         variables=(('input', child),), source=source, window=(node['op'], node['bars'], ddof))
        features[key] = result
        market_features[source][key] = result
        return result

    def condition_group(tree, name, kind):
        nonlocal identity
        rules, conditions = compile_condition(validate_tree(tree, expressions=expressions), operand, identity, named, window)
        identity += len(rules)
        return Group(name, kind, rules,
                     any(rule.left.tick_sensitive or rule.right.tick_sensitive for rule in rules), conditions)

    for group in sorted(config['rule_groups'], key=lambda item: item.get('priority') or 1):
        if not group.get('is_active', True):
            continue
        from dataclasses import replace
        compiled = condition_group(group['condition'], group.get('name', ''), RuleType(group['rule_type']))
        if group.get('setup'):
            raw = group['setup']
            arm = condition_group(raw['arm'], 'Arm', compiled.kind)
            invalidate = condition_group(raw['invalidate'], 'Invalidate', compiled.kind) if raw.get('invalidate') else None
            steps = tuple(condition_group(tree, f'Step {i + 1}', compiled.kind) for i, tree in enumerate(raw['steps']))
            setup = Setup(group['id'], arm, invalidate, steps,
                tuple((name, compile_numeric(tree, operand, named, window)) for name, tree in raw['captures'].items()),
                CandleTimeframe(raw['timeframe']), raw['expires_after_bars'])
            compiled = replace(compiled, setup=setup, tick_sensitive=compiled.tick_sensitive or arm.tick_sensitive or
                (invalidate is not None and invalidate.tick_sensitive) or any(part.tick_sensitive for part in steps) or
                any(value.tick_sensitive for _, value in setup.captures))
        groups.append(compiled)
    entry, exit_config, timing = config['entry_order_config'], config['exit_order_config'], config['time_rule']
    def includes(value, kinds):
        return value.kind in kinds or any(includes(child, kinds) for _, child in value.variables)

    initial_risk = (compile_numeric(validate_tree(config['initial_risk'], expected='number', expressions=expressions), operand, named, window)
                    if config.get('initial_risk') is not None else None)
    if initial_risk is None and any(includes(value, {OperandType.POSITION_RR_RATIO}) for group in groups
           for rule in group.rules for value in (rule.left, rule.right)):
        if any(group.kind == RuleType.STOP_LOSS and any(op not in ('rule', 'all', 'any')
                for op, _, _ in group.conditions) for group in groups):
            raise ValueError('Define an initial risk distance in Markets & size to use reward/risk with nested stop conditions.')
        stops = [rule for group in groups if group.kind == RuleType.STOP_LOSS for rule in group.rules]
        for rule in stops:
            pnl = rule.left.kind in (OperandType.POSITION_PNL_POINTS, OperandType.POSITION_PNL_PERCENTAGE)
            price = rule.left.kind in (OperandType.LTP, OperandType.CLOSE)
            below = pnl or entry.get('entry_side', Side.BUY) == Side.BUY
            comparisons = ((ComparisonOperator.LESS, ComparisonOperator.LESS_EQUAL) if below else
                           (ComparisonOperator.GREATER, ComparisonOperator.GREATER_EQUAL))
            if (not (pnl or price) or rule.comparison not in comparisons or
                    includes(rule.right, set(POSITION_OPERANDS) - {OperandType.ENTRY_PRICE})):
                raise ValueError('Reward/risk requires an unconditional price or negative P&L stop; its threshold cannot depend on reward/risk or current P&L.')
        if not stops:
            raise ValueError('Reward/risk requires a stop-loss rule to define initial risk.')
    operators = {RuleType.ENTRY: LogicalOperator(entry.get('entry_group_operator', LogicalOperator.OR))}
    for kind, key in ((RuleType.STOP_LOSS, 'stop_loss_group_operator'), (RuleType.TARGET, 'target_group_operator'), (RuleType.EXIT, 'exit_group_operator')):
        operators[kind] = LogicalOperator(exit_config.get(key, LogicalOperator.OR))
    # Resolve contract-dependent state once. Changing ATM while flat must clear
    # old premium crossings, but must not erase an underlying-only armed setup.
    def uses_trade(value):
        return (value.kind != OperandType.CONSTANT and value.source == 'trade'
                or any(uses_trade(child) for _, child in value.variables))
    rebind_rules, rebind_setups = set(), set()
    for group in groups:
        parts = (group,) if group.setup is None else (group, group.setup.arm, *group.setup.steps, group.setup.invalidate)
        affected = {rule.identity for part in parts if part is not None for rule in part.rules
                    if uses_trade(rule.left) or uses_trade(rule.right)}
        rebind_rules.update(affected)
        if group.setup and (affected or any(uses_trade(value) for _, value in group.setup.captures)):
            rebind_setups.add(group.setup.identity)
    return Program(version, base, counts, sources, tuple(groups), operators, features,
        Side(entry.get('entry_side', Side.BUY)), calendar, ZoneInfo(timing['timezone']),
        frozenset(day.title() for day in timing.get('trading_days') or []),
        time.fromisoformat(timing['start_time']) if timing.get('start_time') else None,
        time.fromisoformat(timing['end_time']) if timing.get('end_time') else None,
        tuple((time.fromisoformat(item['start']), time.fromisoformat(item['end'])) for item in timing.get('no_trade_windows') or []),
        {role: (*strategy_requirements(config, signal_calendar or calendar if role == 'signal' else calendar, role=role)[1:],
                market_features[role]) for role in market_features},
        market_calendars={'signal': signal_calendar or calendar, 'trade': calendar}, initial_risk=initial_risk,
        rebind_rules=frozenset(rebind_rules), rebind_setups=frozenset(rebind_setups))


class CandleHistoryConflict(ValueError):
    """Published features need rebuilding because a completed bucket changed."""


def _constant_at(value: float, at: datetime) -> float:
    return value


def _calculation_at(calculation: Calculation, readers: tuple, at: datetime) -> float:
    return calculation.evaluate(read(at) for read in readers)


class FeatureGraph:
    """Shared symbol/calendar features; registering a strategy is preparation work."""
    def __init__(self, calendar, *, capacity: int):
        self.calendar, self.capacity = calendar, capacity
        self.features: dict[FeatureKey, Feature | RollingFeature] = {}
        self.completed: dict[str, datetime] = {}
        self.counts: dict[str, int] = {}
        self.completions: dict[str, deque] = {}

    def register(self, program: Program) -> None:
        # Even a newly listed instrument with no completed bars must start
        # building every required timeframe when its first observation arrives.
        for timeframe in program.counts:
            self.counts.setdefault(timeframe, 0)
        def create(kind, parameters, timeframe):
            numerical = {key: value for key, value in parameters.items() if key != 'shift'}
            identity = kind, timeframe, json.dumps(numerical, sort_keys=True, separators=(',', ':'))
            if identity not in self.features:
                source = numerical.get('source', OperandType.CLOSE)
                nested = None if source in PRICE_SOURCES else create(source,
                    normalize_parameters(source, numerical.get('source_params', {})), timeframe)
                self.features[identity] = Feature(kind, numerical, calendar=self.calendar,
                    capacity=max(self.capacity, program.counts[timeframe]), source=nested)
            return self.features[identity]
        def reader(item):
            # Resolve readers once, before ticks. Insertion order is topological:
            # child nodes publish this candle before a window reads them.
            if item.window is not None:
                if item.feature not in self.features:
                    source = reader(item.variables[0][1])
                    self.features[item.feature] = RollingFeature(*item.window, source=source,
                        capacity=max(self.capacity, program.counts[item.timeframe]))
                return self.features[item.feature].at
            if item.feature is not None:
                feature = create(item.kind, item.parameters, item.timeframe)
                shift = int(item.parameters.get('shift', 0))
                # Prepared graphs cross a multiprocessing queue. Bound methods
                # and partials retain readers without unpicklable local closures.
                return partial(feature.at, shift=shift)
            if item.kind == OperandType.CONSTANT:
                value = float(item.parameters['value'])
                return partial(_constant_at, value)
            readers = tuple(reader(value) for _, value in item.variables)
            return partial(_calculation_at, item.calculation, readers)

        for item in program.features.values():
            reader(item)

    def append(self, timeframe: str, candle: Candle) -> None:
        if timeframe in self.completed and candle.closed_at <= self.completed[timeframe]:
            raise CandleHistoryConflict('Repeated or out-of-order candle; prepare a new graph after a history correction.')
        for identity, feature in self.features.items():
            if identity[1] == timeframe:
                feature.update(candle)
        self.completed[timeframe] = candle.closed_at
        self.counts[timeframe] = self.counts.get(timeframe, 0) + 1
        self.completions.setdefault(timeframe, deque(maxlen=self.capacity)).append(
            (candle.closed_at, self.counts[timeframe]))

    def completed_at(self, timeframe: str, at: datetime) -> tuple[datetime | None, int]:
        for completed, count in reversed(self.completions.get(timeframe, ())):
            if completed <= at:
                return completed, count
        return None, 0

    def ready(self, program: Program, at: datetime) -> bool:
        return all(self.completed_at(tf, at)[1] >= count for tf, count in program.counts.items())
