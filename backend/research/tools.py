"""Read-only AI capabilities: market analysis, saved reports, metadata and draft validation.

Handlers return evidence. They never perform persistent user actions; actions.py
owns changes after explicit confirmation. tool_registry.py owns dispatch/accounting.
"""

from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.forms.models import model_to_dict
from rest_framework.exceptions import ValidationError

from .context import research_instrument_ids
from .evaluation import market_rows
from .models import ResearchRun
from .validation import (
    json_data,
    screen_configuration,
    validate_customer_rules,
    validate_draft,
)

# Discovery and builder metadata.


def handle_resolve_instruments(run, arguments):
    from trading.services import TradingInstrumentService

    if (
        set(arguments) != {"query"}
        or not isinstance(arguments["query"], str)
        or not 2 <= len(arguments["query"]) <= 100
    ):
        raise ValidationError("Provide a stock name or symbol between 2 and 100 characters.")
    rows = list(
        TradingInstrumentService.search(arguments["query"], exchange="NSE", instrument_type="STOCK").values(
            "id", "symbol", "sym_ticker", "name"
        )
    )
    exact = [
        row
        for row in rows
        if arguments["query"].upper() in {row["symbol"].upper(), row["sym_ticker"].upper(), row["name"].upper()}
    ]
    selected = exact if len(exact) == 1 else rows
    data = {
        "instruments": selected,
        "ambiguous": len(selected) > 1,
        "query": arguments["query"],
        "selection_required": any(row["id"] not in research_instrument_ids(run) for row in selected),
    }
    return {"data": data}


def handle_get_rule_schema(run, arguments):
    from common.enums import OperandType
    from common.enums_view import get_enum_metadata

    operands = arguments.get("operand_types", [])
    if (
        set(arguments) - {"operand_types"}
        or not isinstance(operands, list)
        or len(operands) > 12
        or any(value not in OperandType.values for value in operands)
    ):
        raise ValidationError("Choose up to twelve supported operand types.")
    metadata = get_enum_metadata()
    keys = (
        "StrategyType",
        "MarketType",
        "Exchange",
        "InstrumentType",
        "OrderType",
        "Side",
        "QuantityType",
        "CandleTimeframe",
        "RuleType",
        "LogicalOperator",
        "ComparisonOperator",
        "OperandGroups",
        "StrategyBuilderDefaults",
        "MathExpressionOperandTypes",
    )
    data = {key: metadata[key] for key in keys}
    data["OperandParameterConfig"] = {key: metadata["OperandParameterConfig"][key] for key in operands}
    return {"data": data}


# Completed-candle market research.


def handle_market(run, arguments, *, name):
    arguments = dict(arguments)
    ids = arguments.pop("instrument_ids", None)
    allowed = research_instrument_ids(run)
    if ids is not None and (
        not isinstance(ids, list) or any(type(value) is not int for value in ids) or set(ids) - set(allowed)
    ):
        raise ValidationError("Select these instruments in a new research request before analyzing them.")
    if name == "analyze_stock":
        indicators = arguments.pop("indicators", [])
        if not isinstance(indicators, list) or len(indicators) > 8 or len(ids or allowed) > 5:
            raise ValidationError("Analyze up to five stocks with at most eight configured indicators.")
        if any(
            not isinstance(item, dict) or set(item) - {"type", "params"} or not item.get("type") for item in indicators
        ):
            raise ValidationError("Each indicator needs an operand type and its supported parameters.")
        arguments["conditions"] = [
            {
                "operand_a_type": item["type"],
                "operand_a_params": item.get("params", {}),
                "comparison": "GT",
                "operand_b_type": "CONSTANT",
                "operand_b_params": {"value": 0},
            }
            for item in indicators
        ] or [
            {
                "operand_a_type": "CLOSE",
                "comparison": "GT",
                "operand_b_type": "CONSTANT",
                "operand_b_params": {"value": 0},
            }
        ]
    arguments.setdefault("timeframe", run.request.get("timeframe", "1D"))
    data = market_rows(
        run,
        screen_configuration(arguments),
        comparison=name != "screen_instruments",
        instrument_ids=ids,
        charts=name == "analyze_stock",
    )
    return {"data": data}


# Saved strategy, backtest and execution reviews.


def handle_get_strategy_snapshot(run, arguments):
    if arguments:
        raise ValidationError("This tool reads only the attached strategy.")
    data = run.request.get("strategy_snapshot")
    if not data:
        raise ValidationError("Attach a strategy to inspect its saved configuration.")
    return {"data": data}


def get_backtest_report(run, backtest_id=None):
    ids = run.request.get("backtest_ids", [])
    backtest_id = backtest_id or (ids[0] if len(ids) == 1 else None)
    if backtest_id not in ids:
        raise ValidationError("Choose one of the attached completed backtests.")
    backtest = (
        BacktestRun.objects.select_related("metrics")
        .filter(pk=backtest_id, user_id=run.user_id, status="COMPLETED")
        .first()
    )
    if not backtest or not hasattr(backtest, "metrics"):
        raise ValidationError("Attach one of your completed backtests with calculated metrics.")
    trades = backtest.trades.all()
    totals = trades.aggregate(trades=Count("id"), net_pnl=Sum("net_pnl"), gross_pnl=Sum("gross_pnl"))
    totals = {key: value if value is not None else 0 for key, value in totals.items()}
    monthly = list(
        trades.annotate(month=TruncMonth("exit_time"))
        .values("month")
        .annotate(trades=Count("id"), net_pnl=Sum("net_pnl"))
        .order_by("month")
    )
    instruments = list(
        trades.values("instrument__symbol")
        .annotate(trades=Count("id"), net_pnl=Sum("net_pnl"))
        .order_by("instrument__symbol")
    )
    exits = list(
        trades.values("exit_reason").annotate(trades=Count("id"), net_pnl=Sum("net_pnl")).order_by("exit_reason")
    )
    trade_fields = ("id", "instrument__symbol", "net_pnl", "entry_time", "exit_time", "exit_reason")
    winners = trades.filter(net_pnl__gt=0).order_by("-net_pnl").values(*trade_fields)[:10]
    losers = trades.filter(net_pnl__lt=0).order_by("net_pnl").values(*trade_fields)[:10]
    return json_data(
        {
            "backtest_id": backtest.pk,
            "name": backtest.name,
            "start_date": backtest.start_date,
            "end_date": backtest.end_date,
            "initial_capital": backtest.initial_capital,
            "slippage_pct": backtest.slippage_pct,
            "include_charges": backtest.include_charges,
            "charge_profile_id": backtest.charge_profile_id,
            "snapshot": backtest_configuration(backtest),
            "metrics": model_to_dict(backtest.metrics, exclude=["id", "run"]),
            "data_quality": backtest.data_quality,
            "totals": totals,
            "diagnostics": backtest.diagnostics or None,
            "monthly": monthly,
            "instruments": instruments,
            "exit_reasons": exits,
            "largest_winners": list(winners),
            "largest_losers": list(losers),
            "assumptions": [
                "Candle replay uses simulated observations; fills follow the saved execution configuration.",
                "Historical results do not establish out-of-sample performance.",
            ],
        }
    )


def handle_get_backtest_report(run, arguments):
    if set(arguments) - {"backtest_id"}:
        raise ValidationError("This tool reads only attached backtests.")
    data = get_backtest_report(run, arguments.get("backtest_id"))
    return {"data": data}


def handle_compare_backtests(run, arguments):
    if arguments or len(run.request.get("backtest_ids", [])) < 2:
        raise ValidationError("Attach at least two completed backtests to compare.")
    reports = [get_backtest_report(run, value) for value in run.request["backtest_ids"]]
    configs = [
        {
            key: item[key]
            for key in (
                "start_date",
                "end_date",
                "initial_capital",
                "slippage_pct",
                "include_charges",
                "charge_profile_id",
                "snapshot",
            )
        }
        for item in reports
    ]
    differences = [key for key in configs[0] if any(item[key] != configs[0][key] for item in configs[1:])]
    data = {
        "reports": reports,
        "differences": differences,
        "limitations": ["Different dates, universes, rules or cost settings limit direct comparison."]
        if differences
        else [],
    }
    return {"data": data}


def handle_get_execution_review(run, arguments):
    if arguments:
        raise ValidationError("This tool reads only the attached execution review.")
    data = run.request.get("execution_evidence")
    if not data:
        raise ValidationError("Attach a journal close or execution report before requesting a review.")
    return {"data": data, "source_as_of": data["as_of"]}


# Conversation evidence and proposed strategy rules.


def handle_get_conversation_evidence(run, arguments):
    if set(arguments) != {"run_id", "evidence_id"}:
        raise ValidationError("Provide an earlier run ID and evidence ID.")
    previous = ResearchRun.objects.filter(
        pk=arguments["run_id"], user_id=run.user_id, session_id=run.session_id, status="COMPLETED", id__lt=run.pk
    ).first()
    if not previous:
        raise ValidationError("Evidence can only be retrieved from an earlier turn in this conversation.")
    source = next((item for item in previous.evidence if item["evidence_id"] == arguments["evidence_id"]), None)
    if not source:
        raise ValidationError("This evidence was not recorded for the selected turn.")
    return {
        **source,
        "source_run_id": source.get("source_run_id", previous.pk),
        "source_as_of": source.get("source_as_of", previous.as_of.isoformat()),
    }


def handle_validate_strategy_draft(run, arguments):
    if set(arguments) != {"draft"}:
        raise ValidationError("Provide a draft object.")
    draft = validate_draft(arguments["draft"], research_instrument_ids(run))
    validate_customer_rules(run, arguments["draft"])
    data = {"valid": True, "draft": draft}
    return {"data": data}
