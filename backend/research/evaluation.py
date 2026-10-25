"""Completed-candle screening through the execution kernel; never creates orders."""

import hashlib
import json
import math
from datetime import timedelta
from heapq import merge
from itertools import groupby
from math import isfinite

import pandas as pd
from common.enums import POSITION_OPERANDS, ExecutionMode, OperandType
from django.conf import settings
from django.core.cache import caches
from execution.compiler import FeatureGraph, Program, compile_strategy, source_windows
from execution.engine import EvaluationUnit
from execution.types import Candle, Tick
from instruments.models import Instrument
from marketdata.calendar import MarketSessionCalendar
from marketdata.candles import available_frame, prepare_frames
from marketdata.history import data_revision
from marketdata.quotes import read_quote
from rest_framework.exceptions import ValidationError

from .context import research_instrument_ids
from .models import ACTIVE_RUN_STATUSES, ResearchRun
from .validation import json_data

SCREEN_OPERAND_TYPES = sorted(set(OperandType.values) - set(POSITION_OPERANDS) - {OperandType.LTP})
cache = caches["research"]


def compile_conditions(config: dict, calendar) -> Program:
    """Validate research inputs before requesting history; reuse its warmup plan."""
    program = compile_strategy(
        {
            **config,
            "entry_order_config": {},
            "exit_order_config": {},
            "time_rule": {**config["time_rule"], "timezone": str(calendar.zone)},
        },
        0,
        calendar=calendar,
    )
    if any(group.tick_sensitive for group in program.groups):
        raise ValueError(
            "Historical research requires completed-candle operands. Use CLOSE instead of LTP; position operands require a trading position."
        )
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
        raise ValueError("Research requires at least two completed base candles.")
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
            yield (
                at,
                timeframe,
                Candle(at - timedelta(microseconds=1), at, row.open, row.high, row.low, row.close, row.volume),
            )

    operands = []
    for at, events in groupby(merge(*(completions(tf, frames[tf]) for tf in program.counts)), key=lambda item: item[0]):
        base_candle = None
        for _, timeframe, candle in events:
            graph.append(timeframe, candle)
            if timeframe == program.base_timeframe:
                base_candle = candle
        if base_candle is None or at < observed[-2] or not graph.ready(program, at):
            continue
        tick = Tick("", 0, at, at.timestamp(), base_candle.close)
        operands = []
        for rule in program.groups[0].rules:
            left, right, hit, _ = unit.evaluate_rule(rule, graph, tick)
            if at == observed[-1] and not (isfinite(left) and isfinite(right)):
                raise ValueError("The configured operand has no valid value after warmup.")
            operands.append({"a": left, "b": right, "passed": hit, "comparison": rule.comparison})
    if not graph.ready(program, observed[-1]):
        raise ValueError("Insufficient completed candles for configured warmup.")
    return operands


def _closed_data(run, instrument, config):
    calendar = MarketSessionCalendar.for_instrument(instrument)
    program = compile_conditions(config, calendar)
    base, requirements, depths = program.base_timeframe, program.counts, program.sources
    timeframes = frozenset(requirements)
    required = max(depths.get("1m", 0), depths.get("1D", 0) * calendar.session_minutes)
    source_limit = 2000 * calendar.session_minutes if timeframes <= {"1D", "1W"} else 60000
    if required > source_limit:
        raise ValidationError("Research warmup exceeds the source-data limit; reduce lookback parameters.")
    windows = source_windows(timeframes, depths, calendar, run.as_of, run.as_of)
    start = min(left for left, _ in windows.values())
    revision = data_revision(instrument.sym_ticker)
    calendar.load_holidays(
        start.astimezone(calendar.zone).date() - timedelta(days=7),
        run.as_of.astimezone(calendar.zone).date() + timedelta(days=7),
    )
    calendar_key = hashlib.sha256(repr(calendar.signature).encode()).hexdigest()[:16]
    cache_key = f"research:frames:v2:{run.pk}:{instrument.pk}:{revision}:{calendar_key}"
    stored = cache.get(cache_key)
    if stored and stored["start"] <= start and timeframes <= set(stored["frames"]):
        if all(
            len(stored["frames"][tf]) >= max(requirements.get(tf, 20), 21 if tf == base else 0) for tf in timeframes
        ):
            return program, stored["frames"], stored["quality"]
    loaded, data_quality = prepare_frames(instrument, timeframes, windows, calendar)
    frames, quality = {}, data_quality["timeframes"]
    for timeframe in [base, *sorted(timeframes - {base})]:
        coverage = quality[timeframe]
        frame = loaded.get(timeframe)
        if not coverage["complete"] or frame is None or frame.empty:
            raise ValidationError(
                f"Historical {timeframe} data is unavailable or still pending: {coverage.get('error') or 'no completed observations'}."
            )
        frame = available_frame(frame, timeframe, calendar)
        frame = frame.loc[frame.index <= run.as_of]
        if len(frame) < max(requirements.get(timeframe, 20), 21 if timeframe == base else 0):
            raise ValidationError(f"Insufficient completed {timeframe} candles for configured warmup.")
        frames[timeframe] = frame
    revision = max(item["revision"] for item in quality.values())
    cache_key = f"research:frames:v2:{run.pk}:{instrument.pk}:{revision}:{calendar_key}"
    cache.set(cache_key, {"start": start, "frames": frames, "quality": quality}, settings.RESEARCH_TIMEOUT_SECONDS + 60)
    return program, frames, quality


def _finite_number(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError("The configured operand has no valid value after warmup.")
    return number


def market_rows(run, config, comparison=False, *, instrument_ids=None, charts=False):
    from .services import update_active_run

    rows, excluded = [], []
    ids = instrument_ids if instrument_ids is not None else research_instrument_ids(run)
    if not ids:
        raise ValidationError("Attach stocks or resolve a symbol before analyzing market data.")
    instruments = Instrument.objects.filter(is_active=True, exchange="NSE", instrument_type="STOCK").in_bulk(ids)
    for instrument_id in ids:
        if not ResearchRun.objects.filter(pk=run.pk, status__in=ACTIVE_RUN_STATUSES).exists():
            raise ValidationError("Research was cancelled.")
        instrument = instruments.get(instrument_id)
        if not instrument:
            excluded.append(
                {"instrument_id": instrument_id, "reason": "Instrument is no longer an available active NSE stock."}
            )
            continue
        try:
            update_active_run(run.pk, progress_message=f"Loading completed candles for {instrument.symbol}")
            program, frames, quality = _closed_data(run, instrument, config)
            frame = frames[program.base_timeframe]
            update_active_run(run.pk, progress_message=f"Evaluating conditions for {instrument.symbol}")
            frame_signature = [
                (
                    tf,
                    quality[tf]["revision"],
                    quality[tf]["updated_at"],
                    len(values),
                    str(values.index[0]),
                    str(values.index[-1]),
                )
                for tf, values in sorted(frames.items())
            ]
            signature = json.dumps(
                json_data([config, frame_signature, program.calendar.signature, run.as_of]), sort_keys=True
            )
            evaluation_key = (
                f"research:evaluation:{run.pk}:{instrument.pk}:{hashlib.sha256(signature.encode()).hexdigest()}"
            )
            operands = cache.get(evaluation_key)
            if operands is None:
                operands = evaluate_conditions(program, frames, as_of=run.as_of)
                cache.set(evaluation_key, operands, settings.RESEARCH_TIMEOUT_SECONDS + 60)
            group = config["rule_groups"][0]
            matched = (
                all(item["passed"] for item in operands)
                if group["logical_operator"] == "AND"
                else any(item["passed"] for item in operands)
            )
            quote = read_quote(instrument.sym_ticker)
            if (
                not quote["available"]
                or pd.Timestamp(quote["timestamp"]) > run.as_of
                or pd.Timestamp(quote["updated_at"]) > run.as_of
            ):
                quote = None
            reference = _finite_number(frame["close"].iloc[-21])
            close = _finite_number(frame["close"].iloc[-1])
            if reference <= 0 or close <= 0:
                raise ValidationError("Historical prices must be positive for return calculations.")
            returns = frame["close"].pct_change().dropna().tail(20)
            rows.append(
                {
                    "instrument_id": instrument.pk,
                    "symbol": instrument.symbol,
                    "ticker": instrument.sym_ticker,
                    "matched": matched,
                    "close": close,
                    "volume": _finite_number(frame["volume"].iloc[-1]),
                    "return_20_bars_pct": (close / reference - 1) * 100,
                    "volatility_20_bars_pct": _finite_number(returns.std(ddof=1) * 100),
                    "observed_at": frame.index[-1],
                    "quote": quote,
                    "operand_values": operands,
                    "coverage": quality,
                    "chart": [
                        {
                            "time": stamp,
                            **{key: _finite_number(value[key]) for key in ("open", "high", "low", "close", "volume")},
                        }
                        for stamp, value in frame.tail(120).iterrows()
                    ]
                    if charts
                    else [],
                }
            )
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            excluded.append({"instrument_id": instrument.pk, "symbol": instrument.symbol, "reason": str(exc)})
    return json_data(
        {
            "timeframe": config["time_rule"]["candle_timeframe"],
            "as_of": run.as_of,
            "total": len(ids),
            "evaluated": len(rows),
            "matched": sum(row["matched"] for row in rows),
            "rows": rows if comparison else [row for row in rows if row["matched"]],
            "excluded": excluded,
            "conditions": config["rule_groups"][0],
        }
    )
