"""Resolve owned attachments once; every research turn keeps its own immutable context."""

from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration
from common.enums import CandleTimeframe
from django.shortcuts import get_object_or_404
from instruments.models import Instrument
from rest_framework.exceptions import ValidationError
from strategies.models import Strategy
from strategies.services import StrategySnapshotService

from .models import ResearchRun

CONTEXT_FIELDS = (
    "strategy_id",
    "backtest_ids",
    "instrument_ids",
    "timeframe",
    "watchlist_id",
    "screen",
    "source_run_id",
    "execution_review",
)
SAVED_CONTEXT_FIELDS = (*CONTEXT_FIELDS, "watchlist_name", "instruments", "execution_evidence")


def active_stocks(ids):
    ids = list(dict.fromkeys(ids))
    rows = list(
        Instrument.objects.filter(pk__in=ids, is_active=True, exchange="NSE", instrument_type="STOCK").values(
            "id", "symbol", "name", "sym_ticker"
        )
    )
    if len(rows) != len(ids):
        raise ValidationError("Research supports active NSE stocks.")
    by_id = {item["id"]: item for item in rows}
    return [by_id[value] for value in ids]


def resolve_context(user, data, saved=None):
    context = {**(saved or {}), **{key: data[key] for key in CONTEXT_FIELDS if key in data}}
    review = context.get("execution_review")
    if review:
        if (
            data.get("refresh")
            or not context.get("execution_evidence")
            or review != (saved or {}).get("execution_review")
        ):
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
    if len(backtests) != len(ids):
        raise ValidationError("Attach only your completed backtests.")
    context["backtest_ids"] = ids
    context["backtests"] = [
        {"id": item.pk, "name": item.name, "snapshot": backtest_configuration(item)} for item in backtests
    ]
    snapshot = snapshot or (context["backtests"][0]["snapshot"] if len(backtests) == 1 else None)
    context["strategy_snapshot"] = snapshot
    instruments = context.get("instrument_ids", [])
    context.pop("watchlist_name", None)
    if context.get("watchlist_id"):
        from trading.models import Watchlist

        watchlist = get_object_or_404(Watchlist, pk=context["watchlist_id"], user=user)
        context["watchlist_name"] = watchlist.name
        instruments = list(
            watchlist.instruments.filter(is_active=True, exchange="NSE", instrument_type="STOCK").values_list(
                "id", flat=True
            )
        )
    elif not instruments and snapshot:
        instruments = [item["instrument_id"] for item in snapshot.get("watchlist_instruments", [])]
    context["instruments"] = active_stocks(instruments)
    context["instrument_ids"] = [item["id"] for item in context["instruments"]]
    timeframe = context.get("timeframe") or (snapshot or {}).get("time_rule", {}).get("candle_timeframe") or "1D"
    if timeframe not in CandleTimeframe.values:
        raise ValidationError("Select a supported research timeframe.")
    context["timeframe"] = timeframe
    if context.get("source_run_id"):
        get_object_or_404(ResearchRun, pk=context["source_run_id"], user=user, status=ResearchRun.Status.COMPLETED)
    return context


def research_instrument_ids(run):
    """Tools use only the universe accepted at this run's user-action boundary."""
    return sorted(set(run.request.get("instrument_ids", [])))


def service_payload(run):
    """The HTTP contract includes only accepted context, recent text and selected tools."""
    from django.conf import settings
    from django.core import signing

    from .tool_registry import compact_evidence, tool_definitions

    history = run.session.runs.filter(status=ResearchRun.Status.COMPLETED).exclude(pk=run.pk).order_by("-id")[:6]
    keys = ("instrument_ids", "instruments", "timeframe", "strategy_id", "backtest_ids", "draft_context")
    context = {key: run.request[key] for key in keys if key in run.request}
    context.update(
        has_strategy_snapshot=bool(run.request.get("strategy_snapshot")),
        backtests=[{"id": item["id"], "name": item["name"]} for item in run.request.get("backtests", [])],
        recorded_evidence=[compact_evidence(item) for item in run.evidence],
        screen_data_policy="Analysis uses completed candles. CLOSE is not live LTP; strategy drafts can use LTP.",
    )
    return {
        "prompt": run.prompt,
        "run_token": signing.dumps({"run_id": run.pk, "user_id": run.user_id}, salt="research-run"),
        "as_of": run.as_of.isoformat(),
        "deadline": run.started_at.timestamp() + settings.RESEARCH_TIMEOUT_SECONDS,
        "max_tool_calls": max(0, settings.RESEARCH_MAX_TOOL_CALLS - run.tool_attempts),
        "tools": tool_definitions(run),
        "context": context,
        "history": [
            {
                "run_id": item.pk,
                "prompt": item.prompt or "Market screen",
                "answer": item.result.get("answer", ""),
                "as_of": item.as_of.isoformat(),
                "draft_evidence_id": item.result.get("draft_evidence_id"),
                "evidence": [{"evidence_id": value["evidence_id"], "tool": value["tool"]} for value in item.evidence],
            }
            for item in reversed(list(history))
        ],
    }
