"""Research uses the same serializers and parameter defaults as the builder."""

from common.validation import validate_data
import json
import re
from typing import cast

from common.enums import CandleTimeframe, LogicalOperator, OperandType
from strategies.specification.operands import get_operand_parameter_config
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.exceptions import ValidationError
from strategies.serializers import (
    StrategyCreateSerializer,
)

from .serializers import ScreenConditionSerializer

SCREEN_DEFAULTS = {'timeframe': CandleTimeframe.D1, 'logical_operator': LogicalOperator.AND}


def json_data(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def validate_screen_condition(data):
    if not isinstance(data, dict):
        raise ValidationError("Each rule must be an object.")
    serializer = cast(ScreenConditionSerializer, ScreenConditionSerializer(data=data))
    unknown = set(data) - set(serializer.fields)
    if unknown:
        raise ValidationError(f"Unsupported rule fields: {', '.join(sorted(unknown))}.")
    result = validate_data(serializer)
    # ScreenConditionSerializer normalizes defaults once; research additionally rejects unknown keys.
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


def validate_draft(draft):
    """AI proposals use Studio's document and compiler, without a second builder."""
    from strategies.definitions import CONFIG_FIELDS, document_from_snapshot, validate_definition, compile_preview
    from strategies.models import Strategy
    if not isinstance(draft, dict):
        raise ValidationError('Strategy draft must be an object.')
    base_fields = {'name', 'description', 'strategy_type', 'market_type', 'exchange', 'instrument_type'}
    allowed = base_fields | set(CONFIG_FIELDS) | {'schema_version', 'semantics_version', 'expressions', 'initial_risk'}
    if set(draft) - allowed:
        raise ValidationError(f'Unsupported draft fields: {sorted(set(draft) - allowed)}.')
    serializer = StrategyCreateSerializer(data={key: draft[key] for key in base_fields if key in draft})
    base = validate_data(serializer)
    try:
        document = validate_definition(document_from_snapshot(draft))
    except (ValueError, KeyError) as exc:
        raise ValidationError(f'Invalid Studio draft: {exc}') from None
    strategy = Strategy(**base, definition=document)
    result = {**{key: getattr(strategy, key) for key in base_fields}, **document}
    # Compilation validates source clocks, formula dependencies and risk units.
    try:
        compile_preview(strategy, document)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
    return json_data(result)


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
            or any(not isinstance(value, str) for value in values)
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
    return result


def screen_configuration(arguments):
    if not isinstance(arguments, dict):
        raise ValidationError("Screening conditions must be an object.")
    if set(arguments) - {"timeframe", "conditions", "logical_operator"}:
        raise ValidationError("Unsupported screening fields.")
    timeframe = arguments.get("timeframe", SCREEN_DEFAULTS['timeframe'])
    operator = arguments.get("logical_operator", SCREEN_DEFAULTS['logical_operator'])
    conditions = arguments.get("conditions", [])
    if timeframe not in CandleTimeframe.values or operator not in LogicalOperator.values:
        raise ValidationError("Choose a supported timeframe and group operator.")
    if not isinstance(conditions, list) or not conditions:
        raise ValidationError("Provide at least one screening condition.")
    rules = [validate_screen_condition(value) for value in conditions]
    if any(not rule["is_active"] for rule in rules):
        raise ValidationError("Screening conditions must be active.")
    return {
        "time_rule": {"candle_timeframe": timeframe},
        "rule_groups": [{"rule_type": "ENTRY", "logical_operator": operator, "rules": rules}],
    }
