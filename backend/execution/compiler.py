"""Compile immutable strategy snapshots once, outside the market-event loop."""
from __future__ import annotations

import ast
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, time
from math import ceil, isfinite
from zoneinfo import ZoneInfo

from common.enums import CandleTimeframe, ComparisonOperator, INDICATOR_OPERANDS, LogicalOperator, OperandType, POSITION_OPERANDS, RuleType, Side, get_operand_parameter_config, get_operand_parameter_defaults
from marketdata.contracts import interval_minutes, source_timeframe
from rules_engine.math_expressions import parse_arithmetic_expression

from .features import Feature
from .types import Candle

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


def strategy_requirements(config: dict, calendar) -> tuple[str, dict, dict]:
    """One history plan for admission, data warmup, research and compilation."""
    base = CandleTimeframe(config['time_rule']['candle_timeframe'])
    counts = {base: MIN_WARMUP_BARS}

    def include(kind, params, timeframe):
        timeframe = CandleTimeframe(timeframe)
        counts[timeframe] = max(counts.get(timeframe, 0), _operand_warmup(kind, params, timeframe, calendar))
        if kind == OperandType.MATH_EXPRESSION:
            for variable in params['expression']['variables'].values():
                include(variable['type'], variable.get('params', {}), variable.get('timeframe') or timeframe)

    for group in config.get('rule_groups', []):
        if group.get('is_active', True):
            for rule in group.get('rules', []):
                if rule.get('is_active', True):
                    for side in ('a', 'b'):
                        include(rule[f'operand_{side}_type'], rule.get(f'operand_{side}_params') or {},
                                rule.get(f'operand_{side}_timeframe') or base)
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
    expression: ast.AST | None = None
    variables: tuple[tuple[str, 'Operand'], ...] = ()
    tick_sensitive: bool = False


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
    operator: str
    rules: tuple[Rule, ...]
    tick_sensitive: bool


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
    calendar: object
    zone: ZoneInfo
    trading_days: frozenset[str]
    start: time | None
    end: time | None
    no_trade_windows: tuple[tuple[time, time], ...]

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
            if values:
                distances.append((max if group.operator == LogicalOperator.AND else min)(values))
        return ((max if self.group_operators[RuleType.STOP_LOSS] == LogicalOperator.AND else min)(distances)
                if distances else 0.0)

    def allows_entry(self, at: datetime) -> bool:
        local = at.astimezone(self.zone)
        clock = local.time()
        return (self.calendar.is_open(at) and
            (not self.trading_days or local.strftime('%A') in self.trading_days) and
            (self.start is None or clock >= self.start) and (self.end is None or clock <= self.end) and
            not any(left <= clock <= right for left, right in self.no_trade_windows))


def compile_strategy(config: dict, version: int, *, calendar) -> Program:
    base, counts, sources = strategy_requirements(config, calendar)
    features = {}

    def operand(kind: str, params: dict, timeframe: str) -> Operand:
        kind = OperandType(kind)
        timeframe = CandleTimeframe(timeframe or base)
        parameters = normalize_parameters(kind, params)
        if kind == OperandType.MATH_EXPRESSION:
            formula = parameters['expression']
            expression = parse_arithmetic_expression(formula['expression'], formula['variables'])
            variables = tuple((name, operand(spec['type'], spec.get('params', {}), spec.get('timeframe') or timeframe))
                              for name, spec in formula['variables'].items())
            return Operand(kind, timeframe, parameters, expression=expression,
                           variables=variables, tick_sensitive=any(value.tick_sensitive for _, value in variables))
        if kind in POSITION_OPERANDS or kind == OperandType.LTP:
            if parameters.get('shift', 0):
                raise ValueError('Tick and position operands do not support candle shifts; use CLOSE for historical prices.')
            return Operand(kind, timeframe, parameters, tick_sensitive=True)
        if kind == OperandType.CONSTANT:
            return Operand(kind, timeframe, parameters)
        # Shift belongs to the reader, not the indicator. Two shifts reuse one node.
        numerical = {key: value for key, value in parameters.items() if key != 'shift'}
        key = kind, timeframe, json.dumps(numerical, sort_keys=True, separators=(',', ':'))
        result = Operand(kind, timeframe, parameters, feature=key)
        features[key] = result
        return result

    groups, identity = [], 0
    for group in sorted(config['rule_groups'], key=lambda item: item.get('priority') or 1):
        if not group.get('is_active', True):
            continue
        rules = []
        for item in group['rules']:
            if not item.get('is_active', True):
                continue
            identity += 1
            rules.append(Rule(identity,
                operand(item['operand_a_type'], item.get('operand_a_params') or {}, item.get('operand_a_timeframe') or base),
                ComparisonOperator(item['comparison']),
                operand(item['operand_b_type'], item.get('operand_b_params') or {}, item.get('operand_b_timeframe') or base)))
        if rules:
            groups.append(Group(group.get('name', ''), RuleType(group['rule_type']),
                LogicalOperator(group.get('logical_operator', LogicalOperator.AND)), tuple(rules),
                any(rule.left.tick_sensitive or rule.right.tick_sensitive for rule in rules)))
    entry, exit_config, timing = config['entry_order_config'], config['exit_order_config'], config['time_rule']
    def includes(value, kinds):
        return value.kind in kinds or any(includes(child, kinds) for _, child in value.variables)

    if any(includes(value, {OperandType.POSITION_RR_RATIO}) for group in groups
           for rule in group.rules for value in (rule.left, rule.right)):
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
    return Program(version, base, counts, sources, tuple(groups), operators, features,
        Side(entry.get('entry_side', Side.BUY)), calendar, ZoneInfo(timing['timezone']),
        frozenset(day.title() for day in timing.get('trading_days') or []),
        time.fromisoformat(timing['start_time']) if timing.get('start_time') else None,
        time.fromisoformat(timing['end_time']) if timing.get('end_time') else None,
        tuple((time.fromisoformat(item['start']), time.fromisoformat(item['end'])) for item in timing.get('no_trade_windows') or []))


class CandleHistoryConflict(ValueError):
    """Published features need rebuilding because a completed bucket changed."""


class FeatureGraph:
    """Shared symbol/calendar features; registering a strategy is preparation work."""
    def __init__(self, calendar, *, capacity: int):
        self.calendar, self.capacity = calendar, capacity
        self.features: dict[FeatureKey, Feature] = {}
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
        for item in program.features.values():
            create(item.kind, item.parameters, item.timeframe)

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
