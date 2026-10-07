"""Resolve owned attachments once; every research turn keeps its own immutable context."""
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from common.enums import CandleTimeframe
from instruments.models import Instrument
from strategies.models import Strategy
from strategies.services import StrategySnapshotService
from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration


def active_stocks(ids):
    ids = list(dict.fromkeys(ids))
    if len(ids) > 50:
        raise ValidationError("Select at most 50 instruments.")
    rows = list(Instrument.objects.filter(pk__in=ids, is_active=True, exchange="NSE", instrument_type="STOCK")
                .values("id", "symbol", "name", "sym_ticker"))
    if len(rows) != len(ids):
        raise ValidationError("Research supports active NSE stocks.")
    by_id = {item["id"]: item for item in rows}
    return [by_id[value] for value in ids]


def resolve_context(user, data, saved=None):
    context = {**(saved or {}), **{key: data[key] for key in
               ("strategy_id", "backtest_ids", "instrument_ids", "timeframe", "use_watchlist", "screen", "source_run_id", "execution_review") if key in data}}
    review = context.get("execution_review")
    if review:
        if data.get("refresh") or not context.get("execution_evidence") or review != (saved or {}).get("execution_review"):
            from analytics.services import execution_review_context
            context["execution_review"], context["execution_evidence"] = execution_review_context(user, review)
    else:
        context.pop("execution_evidence", None)
    snapshot = None
    if context.get("strategy_id"):
        strategy = get_object_or_404(Strategy, pk=context["strategy_id"], user=user)
        snapshot = StrategySnapshotService._serialize_strategy(strategy)
    ids = list(dict.fromkeys(context.get("backtest_ids", [])))
    backtests = list(BacktestRun.objects.filter(pk__in=ids, user=user, status="COMPLETED"))
    if len(backtests) != len(ids) or len(ids) > 3:
        raise ValidationError("Attach up to three of your completed backtests.")
    context["backtest_ids"] = ids
    context["backtests"] = [{"id": item.pk, "name": item.name, "snapshot": backtest_configuration(item)} for item in backtests]
    snapshot = snapshot or (context["backtests"][0]["snapshot"] if len(backtests) == 1 else None)
    context["strategy_snapshot"] = snapshot
    instruments = context.get("instrument_ids", [])
    if context.get("use_watchlist"):
        from trading.models import Watchlist
        watchlist = Watchlist.objects.filter(user=user).first()
        instruments = list(watchlist.instruments.filter(is_active=True, exchange="NSE", instrument_type="STOCK")
                           .values_list("id", flat=True)) if watchlist else []
    elif not instruments and snapshot:
        instruments = [item["instrument_id"] for item in snapshot.get("watchlist_instruments", [])]
    context["instruments"] = active_stocks(instruments)
    context["instrument_ids"] = [item["id"] for item in context["instruments"]]
    timeframe = context.get("timeframe") or (snapshot or {}).get("time_rule", {}).get("candle_timeframe") or "1D"
    if timeframe not in CandleTimeframe.values:
        raise ValidationError("Select a supported research timeframe.")
    context["timeframe"] = timeframe
    if context.get("source_run_id"):
        from .models import ResearchRun
        source = get_object_or_404(ResearchRun, pk=context["source_run_id"], user=user, status="COMPLETED")
        context["source_session_id"] = source.session_id
    return context


def research_instrument_ids(run):
    ids = set(run.request.get("instrument_ids", []))
    ids.update(item["instrument_id"] for item in run.request.get("draft_context", {}).get("draft", {}).get("watchlist_instruments", []))
    for item in run.evidence:
        data = item.get("data", {})
        if item.get("tool") == "resolve_instruments" and not data.get("ambiguous"):
            ids.update(row["id"] for row in data.get("instruments", []))
        ids.update(row["instrument_id"] for row in data.get("rows", []))
        if item.get("tool") == "validate_strategy_draft":
            ids.update(row["instrument_id"] for row in data.get("draft", {}).get("watchlist_instruments", []))
    return sorted(ids)
