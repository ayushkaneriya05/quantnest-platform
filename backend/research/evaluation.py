"""Completed-candle screening through the execution kernel; never creates orders."""
from datetime import timedelta
from heapq import merge
from itertools import groupby
from math import isfinite

from common.enums import ExecutionMode, OperandType, POSITION_OPERANDS
from execution.compiler import FeatureGraph, Program, compile_strategy
from execution.engine import EvaluationUnit
from execution.types import Candle, Tick

SCREEN_OPERAND_TYPES = sorted(set(OperandType.values) - set(POSITION_OPERANDS) - {OperandType.LTP})


def compile_conditions(config: dict, calendar) -> Program:
    """Validate research inputs before requesting history; reuse its warmup plan."""
    program = compile_strategy({**config, 'entry_order_config': {}, 'exit_order_config': {},
        'time_rule': {**config['time_rule'], 'timezone': str(calendar.zone)}}, 0, calendar=calendar)
    if any(group.tick_sensitive for group in program.groups):
        raise ValueError('Historical research requires completed-candle operands. Use CLOSE instead of LTP; position operands require a trading position.')
    return program


def evaluate_conditions(program: Program, frames: dict, *, as_of) -> list[dict]:
    """Frames are indexed by candle COMPLETION, as supplied by available_frame.

    Merge completions before evaluating a base candle, so simultaneous timeframe
    closes are visible together. Future/forming candles never reach the graph.
    Only the last two base observations need comparisons: the first seeds crosses.
    Indicators still consume all warmup bars, with bounded retained history.
    """
    base = frames[program.base_timeframe]
    observed = base.index[base.index <= as_of]
    if len(observed) < 2:
        raise ValueError('Research requires at least two completed base candles.')
    graph = FeatureGraph(program.calendar, capacity=max(program.counts.values()) + 2)
    graph.register(program)
    unit = EvaluationUnit((ExecutionMode.BACKTEST, 0, 0), (ExecutionMode.BACKTEST, 0), program)

    def completions(timeframe, frame):
        for row in frame.itertuples():
            at = row.Index.to_pydatetime()
            if at > as_of:
                break
            # Features use completion/session identity; opening time is not used
            # for historical rule evaluation or simulated fills here.
            yield at, timeframe, Candle(at - timedelta(microseconds=1), at,
                row.open, row.high, row.low, row.close, row.volume)

    operands = []
    for at, events in groupby(merge(*(completions(tf, frames[tf]) for tf in program.counts)), key=lambda item: item[0]):
        base_candle = None
        for _, timeframe, candle in events:
            graph.append(timeframe, candle)
            if timeframe == program.base_timeframe:
                base_candle = candle
        if base_candle is None or at < observed[-2] or not graph.ready(program, at):
            continue
        tick = Tick('', 0, at, at.timestamp(), base_candle.close)
        operands = []
        for rule in program.groups[0].rules:
            left, right, hit, _ = unit.evaluate_rule(rule, graph, tick)
            if at == observed[-1] and not (isfinite(left) and isfinite(right)):
                raise ValueError('The configured operand has no valid value after warmup.')
            operands.append({'a': left, 'b': right, 'passed': hit, 'comparison': rule.comparison})
    if not graph.ready(program, observed[-1]):
        raise ValueError('Insufficient completed candles for configured warmup.')
    return operands
