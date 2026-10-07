"""Deterministic, user-scoped tools. No model-generated code is executed."""
from datetime import timedelta
import math
import hashlib
import json
import logging
import time
import pandas as pd
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.forms.models import model_to_dict
from rest_framework.exceptions import ValidationError
from common.enums import CandleTimeframe, LogicalOperator, OperandType
from instruments.models import Instrument
from marketdata.access import StrategyMarketDataService
from marketdata.calendar import MarketSessionCalendar
from marketdata.services import MarketDataService
from marketdata.quote_store import QuoteStore
from rules_engine.evaluator import RuleEvaluator
from rules_engine.indicators import IndicatorEngine
from rules_engine.metadata import IndicatorRequirementAnalyzer
from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration
from .models import ResearchRun
from .services import ACTIVE, publish_run, update_active_run
from .validation import validate_draft, validate_rule, json_data
from .context import research_instrument_ids

logger = logging.getLogger(__name__)

MAX_TOOLS = 8


def _screen_config(arguments):
    if set(arguments) - {"timeframe", "conditions", "logical_operator"}:
        raise ValidationError("Unsupported screening fields.")
    timeframe = arguments.get("timeframe", "1D")
    operator = arguments.get("logical_operator", "AND")
    conditions = arguments.get("conditions", [])
    if timeframe not in CandleTimeframe.values or operator not in LogicalOperator.values:
        raise ValidationError("Choose a supported timeframe and group operator.")
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 12:
        raise ValidationError("Provide between 1 and 12 screening conditions.")
    rules = [validate_rule(value) for value in conditions]
    if any(not rule["is_active"] for rule in rules):
        raise ValidationError("Screening conditions must be active.")
    return {"time_rule": {"candle_timeframe": timeframe}, "rule_groups": [{
        "rule_type": "ENTRY", "logical_operator": operator,
        "rules": rules}]}


def _closed_data(run, instrument, config):
    calendar = MarketSessionCalendar.for_instrument(instrument)
    base, timeframes = StrategyMarketDataService.required_timeframes(config)
    required = MarketDataService.required_1m_candles(config, session_minutes=calendar.session_minutes)
    source_limit = 2000 * calendar.session_minutes if timeframes <= {"1D", "1W"} else 60000
    if required > source_limit:
        raise ValidationError("Research warmup exceeds the source-data limit; reduce lookback parameters.")
    extra_sessions = 10 if "1W" in timeframes else 5
    start = calendar.warmup_start(run.as_of, required + calendar.session_minutes * extra_sessions, include_weekly="1W" in timeframes)
    cache_key = f"research:frames:{run.pk}:{instrument.pk}"
    stored = cache.get(cache_key)
    requirements = IndicatorRequirementAnalyzer.get_warmup_requirements(config)
    if stored and stored["start"] <= start and timeframes <= set(stored["frames"]):
        if all(len(stored["frames"][tf]) >= max(requirements.get(tf, 20), 21 if tf == base else 0) for tf in timeframes):
            return base, stored["frames"], stored["quality"]
    end = run.as_of.replace(second=0, microsecond=0) - timedelta(microseconds=1)
    daily_end = end
    day = end.astimezone(calendar.zone).date()
    # Include the rest of the week when deciding a weekly candle's final trading day.
    holidays = calendar.load_holidays(start.date(), day + timedelta(days=7))
    while not calendar.is_trading_day(day, holidays) or calendar.session_close(day, holidays) > run.as_of:
        day -= timedelta(days=1)
    daily_end = calendar.session_close(day, holidays)
    frames, quality, fetched = {}, {}, set()
    for timeframe in [base, *sorted(timeframes - {base})]:
        family = "daily" if timeframe in {"1D", "1W"} else "intraday"
        frame, coverage = StrategyMarketDataService.get_backtest_candles(
            instrument.sym_ticker, timeframe, start, daily_end if family == "daily" else end,
            fetch_missing=family not in fetched, calendar=calendar)
        fetched.add(family)
        quality[timeframe] = coverage
        if not coverage["complete"] or frame.empty:
            raise ValidationError(f"Incomplete {timeframe} history after broker backfill: {coverage['missing_count']} missing source candles.")
        frame = frame.copy()
        frame.index = pd.DatetimeIndex([calendar.candle_close(value.to_pydatetime(), timeframe, holidays)
                                       for value in frame.index])
        frame = frame.loc[frame.index <= run.as_of]
        if len(frame) < IndicatorRequirementAnalyzer.get_warmup_requirements(config).get(timeframe, 20):
            raise ValidationError(f"Insufficient completed {timeframe} candles for configured warmup.")
        if timeframe == base and len(frame) < 21:
            raise ValidationError("At least 21 completed candles are needed for 20-bar return and volatility.")
        frames[timeframe] = frame
    cache.set(cache_key, {"start": start, "frames": frames, "quality": quality}, 660)
    return base, frames, quality


def _last_value(value):
    if isinstance(value, pd.Series):
        if value.empty:
            raise ValidationError("The configured operand has no completed observations.")
        value = value.iloc[-1]
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError("The configured operand has no valid value after warmup.")
    return number


def market_rows(run, config, comparison=False, *, instrument_ids=None, charts=False):
    rows, excluded = [], []
    ids = instrument_ids if instrument_ids is not None else research_instrument_ids(run)
    if not ids:
        raise ValidationError("Attach stocks or resolve a symbol before analyzing market data.")
    instruments = Instrument.objects.filter(is_active=True, exchange="NSE", instrument_type="STOCK").in_bulk(ids)
    for instrument_id in ids:
        if not ResearchRun.objects.filter(pk=run.pk, status__in=ACTIVE).exists():
            raise ValidationError("Research was cancelled.")
        instrument = instruments.get(instrument_id)
        if not instrument:
            excluded.append({"instrument_id": instrument_id, "reason": "Instrument is no longer an available active NSE stock."})
            continue
        try:
            update_active_run(run.pk, progress_message=f"Loading completed candles for {instrument.symbol}")
            base, frames, quality = _closed_data(run, instrument, config)
            frame = frames[base]
            update_active_run(run.pk, progress_message=f"Evaluating conditions for {instrument.symbol}")
            frame_signature = [(tf, len(values), str(values.index[0]), str(values.index[-1])) for tf, values in sorted(frames.items())]
            indicator_key = f"research:indicators:{run.pk}:{instrument.pk}:{hashlib.sha256(str(frame_signature).encode()).hexdigest()}"
            previous_indicators = cache.get(indicator_key, {})
            engines = {tf: IndicatorEngine(values) for tf, values in frames.items()}
            for tf, engine in engines.items():
                engine._indicators_cached = previous_indicators.get(tf, {})
            evaluator = RuleEvaluator(frame, mtf_data=frames, indicator_engine=engines[base],
                                      mtf_indicator_engines=engines, instrument=instrument, strict=True)
            operands = []
            for rule in config["rule_groups"][0]["rules"]:
                resolved = {}
                for side in ("a", "b"):
                    resolved[side] = evaluator._resolve_operand(
                        rule[f"operand_{side}_type"], rule.get(f"operand_{side}_params") or {},
                        timeframe=rule.get(f"operand_{side}_timeframe"))
                if isinstance(resolved["a"], pd.Series) and isinstance(resolved["b"], pd.Series):
                    resolved["b"] = resolved["b"].reindex(resolved["a"].index, method="ffill")
                outcomes = evaluator.evaluate_rule(rule).reindex(frame.index, method="ffill").fillna(False)
                operands.append({"a": _last_value(resolved["a"]), "b": _last_value(resolved["b"]),
                                 "passed": bool(outcomes.iloc[-1]), "comparison": rule["comparison"]})
            group = config["rule_groups"][0]
            matched = all(item["passed"] for item in operands) if group["logical_operator"] == "AND" else any(item["passed"] for item in operands)
            cache.set(indicator_key, {tf: engine._indicators_cached for tf, engine in engines.items()}, 660)
            quote = QuoteStore.get_latest(instrument.sym_ticker)
            if quote and pd.Timestamp(quote.get("updated_at")) > run.as_of:
                quote = None
            reference = _last_value(frame["close"].iloc[-21])
            close = _last_value(frame["close"].iloc[-1])
            if reference <= 0 or close <= 0:
                raise ValidationError("Historical prices must be positive for return calculations.")
            returns = frame["close"].pct_change().dropna().tail(20)
            rows.append({"instrument_id": instrument.pk, "symbol": instrument.symbol,
                         "ticker": instrument.sym_ticker, "matched": matched,
                         "close": close, "volume": _last_value(frame["volume"].iloc[-1]),
                         "return_20_bars_pct": (close / reference - 1) * 100,
                         "volatility_20_bars_pct": _last_value(returns.std(ddof=1) * 100),
                         "observed_at": frame.index[-1], "quote": quote,
                         "operand_values": operands, "coverage": quality,
                         "chart": [{"time": stamp, **{key: _last_value(value[key]) for key in ("open", "high", "low", "close", "volume")}}
                                   for stamp, value in frame.tail(120).iterrows()] if charts else []})
        except (ValidationError, ValueError, TypeError, KeyError) as exc:
            excluded.append({"instrument_id": instrument.pk, "symbol": instrument.symbol, "reason": str(exc)})
    return json_data({"timeframe": config["time_rule"]["candle_timeframe"], "as_of": run.as_of,
                      "total": len(ids), "evaluated": len(rows),
                      "matched": sum(row["matched"] for row in rows),
                      "rows": rows if comparison else [row for row in rows if row["matched"]],
                      "excluded": excluded, "conditions": config["rule_groups"][0]})


def get_backtest_report(run, backtest_id=None):
    ids = run.request.get("backtest_ids", [])
    backtest_id = backtest_id or (ids[0] if len(ids) == 1 else None)
    if backtest_id not in ids:
        raise ValidationError("Choose one of the attached completed backtests.")
    backtest = BacktestRun.objects.select_related("metrics").filter(pk=backtest_id, user_id=run.user_id, status="COMPLETED").first()
    if not backtest or not hasattr(backtest, "metrics"):
        raise ValidationError("Attach one of your completed backtests with calculated metrics.")
    trades = backtest.trades.all()
    totals = trades.aggregate(trades=Count("id"), net_pnl=Sum("net_pnl"), gross_pnl=Sum("gross_pnl"))
    totals = {key: value if value is not None else 0 for key, value in totals.items()}
    monthly = list(trades.annotate(month=TruncMonth("exit_time")).values("month").annotate(trades=Count("id"), net_pnl=Sum("net_pnl")).order_by("month"))
    instruments = list(trades.values("instrument__symbol").annotate(trades=Count("id"), net_pnl=Sum("net_pnl")).order_by("instrument__symbol"))
    exits = list(trades.values("exit_reason").annotate(trades=Count("id"), net_pnl=Sum("net_pnl")).order_by("exit_reason"))
    trade_fields = ("id", "instrument__symbol", "net_pnl", "entry_time", "exit_time", "exit_reason")
    winners = trades.filter(net_pnl__gt=0).order_by("-net_pnl").values(*trade_fields)[:10]
    losers = trades.filter(net_pnl__lt=0).order_by("net_pnl").values(*trade_fields)[:10]
    return json_data({"backtest_id": backtest.pk, "name": backtest.name, "start_date": backtest.start_date,
                      "end_date": backtest.end_date, "initial_capital": backtest.initial_capital,
                      "slippage_pct": backtest.slippage_pct, "include_charges": backtest.include_charges,
                      "charge_profile_id": backtest.charge_profile_id, "snapshot": backtest_configuration(backtest),
                      "metrics": model_to_dict(backtest.metrics, exclude=["id", "run"]),
                      "data_quality": backtest.data_quality, "totals": totals,
                      "diagnostics": backtest.diagnostics or None,
                      "monthly": monthly, "instruments": instruments, "exit_reasons": exits,
                      "largest_winners": list(winners), "largest_losers": list(losers),
                      "assumptions": ["Orders fill at the next candle open.", "Strategy auto-disable rules are not simulated.",
                                      "Historical results do not establish out-of-sample performance."]})


def _calculate_tool(run, name, arguments):
    if not isinstance(arguments, dict):
        raise ValidationError("Tool arguments must be an object.")
    if name in {"screen_instruments", "compare_instruments", "analyze_stock"}:
        arguments = dict(arguments)
        ids = arguments.pop("instrument_ids", None)
        allowed = research_instrument_ids(run)
        if ids is not None and (not isinstance(ids, list) or len(ids) > 50 or any(type(value) is not int for value in ids) or set(ids) - set(allowed)):
            raise ValidationError("Resolve or attach these instruments before requesting analysis.")
        if name == "analyze_stock":
            indicators = arguments.pop("indicators", [])
            if not isinstance(indicators, list) or len(indicators) > 8 or len(ids or allowed) > 5:
                raise ValidationError("Analyze up to five stocks with at most eight configured indicators.")
            if any(not isinstance(item, dict) or set(item) - {"type", "params"} or not item.get("type") for item in indicators):
                raise ValidationError("Each indicator needs an operand type and its supported parameters.")
            arguments["conditions"] = [{"operand_a_type": item["type"], "operand_a_params": item.get("params", {}),
                "comparison": "GT", "operand_b_type": "CONSTANT", "operand_b_params": {"value": 0}} for item in indicators] or [
                    {"operand_a_type": "CLOSE", "comparison": "GT", "operand_b_type": "CONSTANT", "operand_b_params": {"value": 0}}]
        arguments.setdefault("timeframe", run.request.get("timeframe", "1D"))
        data = market_rows(run, _screen_config(arguments), comparison=name != "screen_instruments", instrument_ids=ids, charts=name == "analyze_stock")
    elif name == "resolve_instruments":
        from trading.services import TradingInstrumentService
        if set(arguments) != {"query"} or not isinstance(arguments["query"], str) or not 2 <= len(arguments["query"]) <= 100:
            raise ValidationError("Provide a stock name or symbol between 2 and 100 characters.")
        rows = list(TradingInstrumentService.search(arguments["query"], exchange="NSE", instrument_type="STOCK")
                    .values("id", "symbol", "sym_ticker", "name"))
        exact = [row for row in rows if arguments["query"].upper() in {row["symbol"].upper(), row["sym_ticker"].upper(), row["name"].upper()}]
        selected = exact if len(exact) == 1 else rows
        data = {"instruments": selected, "ambiguous": len(selected) > 1, "query": arguments["query"]}
    elif name == "get_execution_review":
        if arguments:
            raise ValidationError("This tool reads only the attached execution review.")
        data = run.request.get("execution_evidence")
        if not data:
            raise ValidationError("Attach a journal close or execution report before requesting a review.")
        return {"tool": name, "arguments": {}, "data": data, "source_as_of": data["as_of"]}
    elif name == "get_strategy_snapshot":
        if arguments:
            raise ValidationError("This tool reads only the attached strategy.")
        data = run.request.get("strategy_snapshot")
        if not data:
            raise ValidationError("Attach a strategy to inspect its saved configuration.")
    elif name == "get_backtest_report":
        if set(arguments) - {"backtest_id"}:
            raise ValidationError("This tool reads only attached backtests.")
        data = get_backtest_report(run, arguments.get("backtest_id"))
    elif name == "compare_backtests":
        if arguments or len(run.request.get("backtest_ids", [])) < 2:
            raise ValidationError("Attach two or three completed backtests to compare.")
        reports = [get_backtest_report(run, value) for value in run.request["backtest_ids"]]
        configs = [{key: item[key] for key in ("start_date", "end_date", "initial_capital", "slippage_pct", "include_charges", "charge_profile_id", "snapshot")} for item in reports]
        differences = [key for key in configs[0] if any(item[key] != configs[0][key] for item in configs[1:])]
        data = {"reports": reports, "differences": differences,
                "limitations": ["Different dates, universes, rules or cost settings limit direct comparison."] if differences else []}
    elif name == "get_conversation_evidence":
        if set(arguments) != {"run_id", "evidence_id"}:
            raise ValidationError("Provide an earlier run ID and evidence ID.")
        previous = ResearchRun.objects.filter(pk=arguments["run_id"], user_id=run.user_id,
            session_id=run.session_id, status="COMPLETED", id__lt=run.pk).first()
        if not previous:
            raise ValidationError("Evidence can only be retrieved from an earlier turn in this conversation.")
        source = next((item for item in previous.evidence if item["evidence_id"] == arguments["evidence_id"]), None)
        if not source:
            raise ValidationError("This evidence was not recorded for the selected turn.")
        return {**source, "source_run_id": source.get("source_run_id", previous.pk),
                "source_as_of": source.get("source_as_of", previous.as_of.isoformat())}
    elif name == "validate_strategy_draft":
        if set(arguments) != {"draft"}:
            raise ValidationError("Provide a draft object.")
        data = {"valid": True, "draft": validate_draft(arguments["draft"], research_instrument_ids(run))}
    else:
        raise ValidationError("This tool is not allowed.")
    return {"tool": name, "arguments": json_data(arguments), "data": json_data(data)}


def execute_tool(run, name, arguments):
    """Reserve attempts before work; cache artifacts and frames only for this run."""
    key = hashlib.sha256(json.dumps([name, arguments], sort_keys=True, default=str).encode()).hexdigest()
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().filter(pk=run.pk).first()
        if not current or current.status not in ACTIVE:
            raise ValidationError("Research was cancelled.")
        if current.tool_attempts >= MAX_TOOLS:
            raise ValidationError("Research exceeded its eight-tool budget.")
        current.tool_attempts += 1
        current.save(update_fields=["tool_attempts"])
        run = current
        cached = next((item for item in current.evidence if item.get("cache_key") == key), None)
        if cached:
            return cached
    started = time.monotonic()
    try:
        calculated = _calculate_tool(run, name, arguments)
    finally:
        logger.info("Research tool run=%s tool=%s duration_ms=%d", run.pk, name, (time.monotonic() - started) * 1000)
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().get(pk=run.pk)
        if current.status not in ACTIVE:
            raise ValidationError("Research was cancelled.")
        evidence = {**calculated, "evidence_id": f"E{len(current.evidence) + 1}", "cache_key": key,
                    "source_run_id": calculated.get("source_run_id", run.pk),
                    "source_as_of": calculated.get("source_as_of", run.as_of.isoformat())}
        current.evidence = [*current.evidence, evidence]
        current.progress_message = f"Completed {name.replace('_', ' ')}"
        current.revision += 1
        current.save(update_fields=["evidence", "progress_message", "revision", "updated_at"])
        publish_run(current)
    return evidence
