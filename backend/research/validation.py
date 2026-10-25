"""Research uses the same serializers and parameter defaults as the builder."""

import json
import re

from common.enums import (
    CandleTimeframe,
    InstrumentType,
    LogicalOperator,
    OperandType,
    RuleType,
    get_operand_parameter_config,
)
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from instruments.models import Instrument
from rest_framework.exceptions import ValidationError
from rules_engine.serializers import (
    PositionSizingRuleSerializer,
    RuleGroupSerializer,
    RuleSerializer,
    TimeRuleSerializer,
)
from strategies.serializers import (
    EntryOrderConfigSerializer,
    ExitOrderConfigSerializer,
    StrategyCreateSerializer,
)

from .models import ResearchRun


def json_data(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def validate_config(serializer_class, data):
    if not isinstance(data, dict):
        raise ValidationError("Configuration must be an object.")
    model = serializer_class.Meta.model
    instance = model()
    serializer = serializer_class(instance)
    allowed = {name for name, field in serializer.fields.items() if not field.read_only} - {"strategy", "rule_group"}
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"Unsupported fields: {', '.join(sorted(unknown))}.")
    # Read model defaults without serializing reverse relations on an unsaved draft.
    defaults = model_to_dict(instance, fields=allowed)
    serializer = serializer_class(instance, data={**defaults, **data}, partial=True)
    for field in ("strategy", "rule_group"):
        if field in serializer.fields:
            serializer.fields[field].read_only = True
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def validate_rule(data, rule_type=RuleType.ENTRY):
    if not isinstance(data, dict):
        raise ValidationError("Each rule must be an object.")
    serializer = RuleSerializer()
    unknown = set(data) - (set(serializer.fields) - {"id", "rule_group"})
    if unknown:
        raise ValidationError(f"Unsupported rule fields: {', '.join(sorted(unknown))}.")
    if not data.get("operand_a_type") or not data.get("operand_b_type") or not data.get("comparison"):
        raise ValidationError("Specify both operands and their comparison.")
    serializer = RuleSerializer(data=data, context={"rule_type": rule_type}, partial=True)
    serializer.is_valid(raise_exception=True)
    result = serializer.validated_data
    result["is_active"] = result.get("is_active", True)
    # RuleSerializer normalizes defaults once; research additionally rejects unknown keys.
    for side in ("a", "b"):
        field = f"operand_{side}_params"
        operand = result[f"operand_{side}_type"]
        _validate_parameter_keys(operand, result.get(field) or {})
    return result


def _validate_parameter_keys(operand, params, *, source=False):
    schema = get_operand_parameter_config(OperandType(operand))
    keys = {item["key"] for item in schema}
    if source:
        keys -= {"source", "shift"}
    elif "source" in keys:
        keys.add("source_params")
    if set(params) - keys:
        raise ValidationError(f"Unsupported {operand} parameters: {', '.join(sorted(set(params) - keys))}.")
    if params.get("source_params"):
        _validate_parameter_keys(params["source"], params["source_params"], source=True)
    if operand == OperandType.MATH_EXPRESSION:
        expression = params.get("expression")
        if not isinstance(expression, dict) or set(expression) - {"expression", "variables"}:
            raise ValidationError("Math expressions need expression text and configured variables.")
        for variable in (expression.get("variables") or {}).values():
            if set(variable) - {"type", "params", "timeframe"}:
                raise ValidationError("Unsupported math variable configuration.")
            _validate_parameter_keys(variable["type"], variable.get("params") or {})


CONFIG_SERIALIZERS = {
    "entry_order_config": EntryOrderConfigSerializer,
    "exit_order_config": ExitOrderConfigSerializer,
    "position_sizing_rule": PositionSizingRuleSerializer,
    "time_rule": TimeRuleSerializer,
}


def validate_draft(draft, instrument_ids):
    if not isinstance(draft, dict):
        raise ValidationError("Strategy draft must be an object.")
    base_fields = {"name", "description", "strategy_type", "market_type", "exchange", "instrument_type"}
    allowed = base_fields | set(CONFIG_SERIALIZERS) | {"rule_groups", "watchlist_instruments"}
    if set(draft) - allowed:
        raise ValidationError(f"Unsupported draft fields: {', '.join(sorted(set(draft) - allowed))}.")
    serializer = StrategyCreateSerializer(data={key: draft[key] for key in base_fields if key in draft})
    serializer.is_valid(raise_exception=True)
    result = dict(serializer.validated_data)
    if (
        result.get("exchange") != "NSE"
        or result.get("instrument_type") != InstrumentType.STOCK
        or result.get("market_type") != "EQUITY"
    ):
        raise ValidationError("Research drafts currently support NSE equities and direct execution routes.")
    for name, config_serializer in CONFIG_SERIALIZERS.items():
        result[name] = validate_config(config_serializer, draft.get(name, {}))
    time_rule = result["time_rule"]
    days = time_rule.get("trading_days")
    if not days or not time_rule.get("start_time") or not time_rule.get("end_time"):
        raise ValidationError("Choose trading days and start/end times.")
    watchlist = draft.get("watchlist_instruments") or [{"instrument_id": value} for value in instrument_ids]
    if not isinstance(watchlist, list):
        raise ValidationError("Watchlist instruments must be a list.")
    ids = [item.get("instrument_id") for item in watchlist if isinstance(item, dict)]
    if (
        not ids
        or any(not isinstance(value, int) or isinstance(value, bool) for value in ids)
        or len(ids) != len(watchlist)
        or len(set(ids)) != len(ids)
        or set(ids) - set(instrument_ids)
    ):
        raise ValidationError("Select unique instruments from this research universe.")
    instruments = Instrument.objects.in_bulk(ids)
    if len(instruments) != len(ids) or any(
        item.exchange != "NSE" or item.instrument_type != InstrumentType.STOCK or not item.is_active
        for item in instruments.values()
    ):
        raise ValidationError("The selected instruments must be active NSE equities.")
    for item in watchlist:
        if set(item) - {"instrument_id", "execution_routes"}:
            raise ValidationError("Unsupported watchlist fields.")
        routes = item.get("execution_routes", [{"route_type": "DIRECT"}])
        if routes != [{"route_type": "DIRECT"}]:
            raise ValidationError("Each instrument must have one DIRECT route.")
    result["watchlist_instruments"] = [
        {"instrument_id": value, "execution_routes": [{"route_type": "DIRECT"}]} for value in ids
    ]
    groups = draft.get("rule_groups", [])
    if not isinstance(groups, list) or not 1 <= len(groups) <= 12:
        raise ValidationError("Provide between 1 and 12 rule groups.")
    result["rule_groups"] = []
    for group in groups:
        if not isinstance(group, dict) or set(group) - {"name", "rule_type", "logical_operator", "priority", "rules"}:
            raise ValidationError("Unsupported rule group fields.")
        config = validate_config(RuleGroupSerializer, {key: value for key, value in group.items() if key != "rules"})
        # Groups are always active on a reviewed draft; retain only its editable fields.
        config.pop("is_active", None)
        rules = group.get("rules", [])
        if not isinstance(rules, list) or not 1 <= len(rules) <= 12:
            raise ValidationError("Each group needs between 1 and 12 rules.")
        config["rules"] = [validate_rule(rule, config["rule_type"]) for rule in rules]
        if any(not rule.get("is_active", True) for rule in config["rules"]):
            raise ValidationError("Draft rules must be active; disable them later in the builder.")
        result["rule_groups"].append(config)
    if not any(group["rule_type"] == RuleType.ENTRY for group in result["rule_groups"]):
        raise ValidationError("A strategy needs an entry group.")
    if not any(group["rule_type"] != RuleType.ENTRY for group in result["rule_groups"]):
        raise ValidationError("Add an exit, stop-loss, or target group.")
    return json_data(result)


UNSUPPORTED_CLAIMS = re.compile(
    r"\b(?:guaranteed|assured|risk[ -]free)\s+(?:profits?|returns?|income)|"
    r"\b(?:i recommend|you should|you must)\s+(?:buy|sell|invest|short)\b|"
    r"\b(?:(?:your|recommended|our) price target(?: is)?|target price is|suitable for your (?:portfolio|risk)|best stocks? to buy)\b",
    re.I,
)


def validate_written_result(result):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return
    text = "\n".join(
        [result.get("answer", ""), *result.get("next_steps", []), *result.get("clarification_questions", [])]
    )
    if UNSUPPORTED_CLAIMS.search(text):
        raise ValidationError(
            "The response crossed the software-only boundary. Ask for an explanation of your own conditions or recorded results."
        )


def validate_customer_rules(run, draft):
    """A new draft must be traceable to explicit user-supplied trading choices."""
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return
    baseline = run.request.get("strategy_snapshot") or run.request.get("draft_context", {}).get("draft", {})
    prompts = [
        run.prompt,
        *ResearchRun.objects.filter(session_id=run.session_id, user_id=run.user_id, pk__lt=run.pk)
        .order_by("-pk")
        .values_list("prompt", flat=True)[:20],
    ]
    text = " ".join(prompts).lower()
    groups = draft.get("rule_groups", [])
    choices_supplied = all(
        re.search(pattern, text)
        for pattern in (
            r"\b(?:entry|enter|buy|long|short)\b",
            r"\b(?:exit|close|sell)\b",
            r"\b(?:minute|hour|daily|day|weekly|1m|5m|15m|1h|1d|1w)\b",
            r"\b(?:quantity|shares|capital|sizing)\b",
        )
    )
    if not baseline and (not groups or not choices_supplied):
        raise ValidationError(
            "Ask the customer to specify entry, exit, timeframe and sizing choices before translating a new draft."
        )
    numeric_choices = {float(value) for value in re.findall(r"(?<![a-z])\d+(?:\.\d+)?", text)}
    if baseline and not run.prompt.strip():
        raise ValidationError("Describe the requested rule change.")
    previous_groups = baseline.get("rule_groups", [])
    for group_index, group in enumerate(groups):
        previous_rules = previous_groups[group_index].get("rules", []) if group_index < len(previous_groups) else []
        for rule_index, rule in enumerate(group.get("rules", [])):
            previous = previous_rules[rule_index] if rule_index < len(previous_rules) else {}
            for field in ("operand_a_params", "operand_b_params"):
                for key, value in (rule.get(field) or {}).items():
                    if key in {"value", "period", "length", "fast", "slow", "signal"}:
                        try:
                            number = float(value)
                        except (TypeError, ValueError):
                            continue
                        if (previous.get(field) or {}).get(key) == value:
                            continue
                        if number not in numeric_choices:
                            raise ValidationError(
                                "A trading threshold or indicator period was not supplied by the customer. Ask for that choice before generating rules."
                            )


def normalize_citations(text, evidence, references):
    """Canonicalize written references using the backend evidence, not model bookkeeping."""

    def replace(match):
        group = match.group(1).strip()
        if not re.fullmatch(r"E\d+(?:\s*[,;]\s*E\d+)*", group):
            raise ValueError("Use individual evidence citations such as [E1] and [E2].")
        ids = re.findall(r"E\d+", group)
        missing = set(ids) - evidence.keys()
        if missing:
            raise ValueError(
                f"Written citations reference evidence unavailable in this run: {', '.join(sorted(missing))}."
            )
        references.extend(ids)
        return " ".join(f"[{value}]" for value in dict.fromkeys(ids))

    # Ordinary bracketed words, such as [EMA], are not evidence references.
    # Evidence links always open our recorded artifact, never a model-supplied URL.
    return re.sub(r"\[(E\d+\b[^\[\]\n]*)\](?:\([^\)\n]*\))?", replace, text)


def finalize_result(run, result):
    fields = {
        "answer",
        "evidence_ids",
        "draft_evidence_id",
        "next_steps",
        "limitations",
        "clarification_questions",
        "artifact_refs",
        "proposed_actions",
    }
    if (
        not isinstance(result, dict)
        or set(result) - fields
        or not isinstance(result.get("answer"), str)
        or not result["answer"].strip()
    ):
        raise ValueError("The research service returned an invalid result.")
    evidence = {item["evidence_id"]: item for item in run.evidence}
    references = result.get("evidence_ids", [])
    if not isinstance(references, list) or any(
        not isinstance(value, str) or value not in evidence for value in references
    ):
        raise ValueError("The response cited evidence that was not calculated by this run.")
    references = list(references)
    result["answer"] = normalize_citations(result["answer"], evidence, references)
    for field in ("next_steps", "limitations", "clarification_questions"):
        values = result.get(field, [])
        if (
            not isinstance(values, list)
            or len(values) > 8
            or any(not isinstance(value, str) or len(value) > 2000 for value in values)
        ):
            raise ValueError(f"Invalid {field} in research response.")
        result[field] = [normalize_citations(value, evidence, references) for value in values]
    # An omitted declaration must not discard a valid, calculated inline citation.
    result["evidence_ids"] = references = list(dict.fromkeys(references))
    artifacts = result.get("artifact_refs", [])
    if not isinstance(artifacts, list) or any(
        not isinstance(value, str) or value not in evidence for value in artifacts
    ):
        raise ValueError("An artifact reference was not recorded for this run.")
    result["artifact_refs"] = list(dict.fromkeys(artifacts or references))
    draft_id = result.get("draft_evidence_id")
    if draft_id:
        if not isinstance(draft_id, str):
            raise ValueError("The proposed strategy draft has an invalid evidence reference.")
        item = evidence.get(draft_id)
        if not item or item["tool"] != "validate_strategy_draft":
            raise ValueError("The proposed strategy draft has not passed backend validation.")
        result["draft"] = item["data"]["draft"]
    validate_written_result(result)
    return result


def screen_configuration(arguments):
    if not isinstance(arguments, dict):
        raise ValidationError("Screening conditions must be an object.")
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
    return {
        "time_rule": {"candle_timeframe": timeframe},
        "rule_groups": [{"rule_type": "ENTRY", "logical_operator": operator, "rules": rules}],
    }
