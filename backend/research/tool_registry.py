"""The single source of tool schemas, handlers and model-facing projections."""

import hashlib
import json
import logging
import time
from functools import lru_cache, partial

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import ACTIVE_RUN_STATUSES, ResearchRun
from .validation import json_data

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def registry():
    from common.enums import CandleTimeframe, ComparisonOperator, LogicalOperator

    from . import tools
    from .evaluation import SCREEN_OPERAND_TYPES

    screen_operand_types = SCREEN_OPERAND_TYPES
    # Historical tools accept only the completed-candle operands supplied by Django.
    rule = {
        "type": "object",
        "properties": {
            "operand_a_type": {"type": "string", "enum": screen_operand_types},
            "operand_a_params": {"type": "object"},
            "operand_a_timeframe": {"type": "string", "enum": CandleTimeframe.values},
            "comparison": {"type": "string", "enum": ComparisonOperator.values},
            "operand_b_type": {"type": "string", "enum": screen_operand_types},
            "operand_b_params": {"type": "object"},
            "operand_b_timeframe": {"type": "string", "enum": CandleTimeframe.values},
        },
        "required": ["operand_a_type", "comparison", "operand_b_type"],
    }
    screen = {
        "type": "object",
        "properties": {
            "timeframe": {"type": "string", "enum": CandleTimeframe.values},
            "logical_operator": {"type": "string", "enum": LogicalOperator.values},
            "conditions": {"type": "array", "items": rule, "minItems": 1, "maxItems": 12},
        },
        "required": ["timeframe", "conditions"],
    }
    screen["properties"]["instrument_ids"] = {"type": "array", "items": {"type": "integer"}}
    registered = {}

    def add(name, handler, description, parameters, *, context_field="", minimum=1):
        registered[name] = {
            "definition": {"name": name, "description": description, "parameters": parameters},
            "handler": handler,
            "context_field": context_field,
            "minimum": minimum,
        }

    # Discovery and builder metadata.
    add(
        "resolve_instruments",
        tools.handle_resolve_instruments,
        "Find an active NSE stock by symbol or name. Ask the user to select new stocks for a new request; the current analysis universe is fixed.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    add(
        "get_rule_schema",
        tools.handle_get_rule_schema,
        "Read builder choices and defaults, plus parameter schemas for the requested operand types. Fetch this before constructing rules.",
        {
            "type": "object",
            "properties": {"operand_types": {"type": "array", "items": {"type": "string"}, "maxItems": 12}},
        },
    )

    # Completed-candle market research.
    add(
        "screen_instruments",
        partial(tools.handle_market, name="screen_instruments"),
        "Evaluate entry rules on the latest completed candles for the selected universe; returns matches and exclusions.",
        screen,
        context_field="instrument_ids",
    )
    add(
        "compare_instruments",
        partial(tools.handle_market, name="compare_instruments"),
        "Return all evaluated instruments with rule values, 20-bar return and 20-bar volatility. To compare without filtering use CLOSE > CONSTANT 0.",
        screen,
        context_field="instrument_ids",
    )
    add(
        "analyze_stock",
        partial(tools.handle_market, name="analyze_stock"),
        "Analyze up to five stocks selected in this run's frozen context with configured indicators and bounded charts.",
        {
            "type": "object",
            "properties": {
                "instrument_ids": {"type": "array", "items": {"type": "integer"}, "maxItems": 5},
                "timeframe": {"type": "string", "enum": CandleTimeframe.values},
                "indicators": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": screen_operand_types},
                            "params": {"type": "object"},
                        },
                        "required": ["type"],
                    },
                },
            },
        },
        context_field="instrument_ids",
    )

    # Saved strategy, backtest and execution reviews.
    add(
        "get_strategy_snapshot",
        tools.handle_get_strategy_snapshot,
        "Read the strategy configuration frozen at request creation. No other strategy IDs are accepted.",
        {"type": "object", "properties": {}},
        context_field="strategy_snapshot",
    )
    add(
        "get_backtest_report",
        tools.handle_get_backtest_report,
        "Read actual metrics, diagnostics, costs and saved snapshot for an attached completed backtest.",
        {"type": "object", "properties": {"backtest_id": {"type": "integer"}}},
        context_field="backtest_ids",
    )
    add(
        "compare_backtests",
        tools.handle_compare_backtests,
        "Compare the attached completed backtests and their saved configurations. At least two are required.",
        {"type": "object", "properties": {}},
        context_field="backtest_ids",
        minimum=2,
    )
    add(
        "get_execution_review",
        tools.handle_get_execution_review,
        "Read the attached owned execution report or selected close, with its original time, P&L basis and optional user assessments.",
        {"type": "object", "properties": {}},
        context_field="execution_evidence",
    )

    # Conversation evidence and proposed strategy rules.
    add(
        "get_conversation_evidence",
        tools.handle_get_conversation_evidence,
        "Retrieve an earlier artifact in this conversation and preserve its observation time.",
        {
            "type": "object",
            "properties": {"run_id": {"type": "integer"}, "evidence_id": {"type": "string"}},
            "required": ["run_id", "evidence_id"],
        },
    )
    add(
        "validate_strategy_draft",
        tools.handle_validate_strategy_draft,
        "Validate a full draft using the existing strategy builder serializers. The draft fields are name, description, strategy_type, market_type, exchange, instrument_type, time_rule, entry_order_config, exit_order_config, position_sizing_rule, watchlist_instruments, rule_groups. Each group has name, rule_type, logical_operator, priority and rules; each rule uses the screening rule fields with operands from get_rule_schema, including live LTP and exit position state. Watchlist items contain instrument_id and execution_routes [{route_type: DIRECT}]. Omit all database IDs except instrument_id.",
        {"type": "object", "properties": {"draft": {"type": "object"}}, "required": ["draft"]},
        context_field="instrument_ids",
    )
    return registered


def _compact_data(data):
    """Keep chart series and trade examples in Django, retaining observations and rules."""
    if "rows" in data:
        data = {
            **data,
            "rows": [
                {key: value for key, value in row.items() if key not in {"chart", "coverage"}} for row in data["rows"]
            ],
        }
    data = {key: value for key, value in data.items() if key not in {"largest_winners", "largest_losers"}}
    if "reports" in data:
        data = {**data, "reports": [_compact_data(report) for report in data["reports"]]}
    return data


def compact_evidence(evidence):
    """Use the common projection without altering its persisted evidence or provenance."""
    data = _compact_data(evidence["data"])
    return {key: value for key, value in {**evidence, "data": data}.items() if key not in {"cache_key", "arguments"}}


def tool_available(tool, run):
    field = tool["context_field"]
    return not field or len(run.request.get(field) or ()) >= tool["minimum"]


def tool_definitions(run):
    return [tool["definition"] for tool in registry().values() if tool_available(tool, run)]


def execute_tool(run, name, arguments):
    """Reserve attempts before work; cache artifacts and frames only for this run."""
    if not isinstance(arguments, dict):
        raise ValidationError("Tool arguments must be an object.")
    from .services import publish_run

    tool = registry().get(name)
    if tool is None or not tool_available(tool, run):
        raise ValidationError("This tool is not available for the selected context.")
    key = hashlib.sha256(json.dumps([name, arguments], sort_keys=True, default=str).encode()).hexdigest()
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().filter(pk=run.pk).first()
        if not current or current.status not in ACTIVE_RUN_STATUSES:
            raise ValidationError("Research was cancelled.")
        cached = next((item for item in current.evidence if item.get("cache_key") == key), None)
        if cached:
            return cached
        if current.tool_attempts >= settings.RESEARCH_MAX_TOOL_CALLS:
            raise ValidationError("Tool limit reached. Complete the answer from existing evidence.")
        current.tool_attempts += 1
        current.save(update_fields=["tool_attempts"])
        run = current
    started = time.monotonic()
    try:
        calculated = json_data(tool["handler"](run, arguments))
    finally:
        logger.info("Research tool run=%s tool=%s duration_ms=%d", run.pk, name, (time.monotonic() - started) * 1000)
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().get(pk=run.pk)
        if current.status not in ACTIVE_RUN_STATUSES:
            raise ValidationError("Research was cancelled.")
        evidence = {
            "tool": name,
            "arguments": json_data(arguments),
            **calculated,
            "evidence_id": f"E{len(current.evidence) + 1}",
            "cache_key": key,
            "source_run_id": calculated.get("source_run_id", run.pk),
            "source_as_of": calculated.get("source_as_of", run.as_of.isoformat()),
        }
        current.evidence = [*current.evidence, evidence]
        current.progress_message = f"Completed {name.replace('_', ' ')}"
        current.revision += 1
        current.save(update_fields=["evidence", "progress_message", "revision", "updated_at"])
        publish_run(current)
    return evidence
