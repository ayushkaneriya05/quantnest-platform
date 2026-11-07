"""Research uses the same serializers and parameter defaults as the builder."""

import json
import re

from common.enums import CandleTimeframe, InstrumentType, LogicalOperator, OperandType, RuleType
from strategies.specification.operands import get_operand_parameter_config
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from instruments.models import Instrument
from rest_framework.exceptions import ValidationError
from strategies.serializers import (
    StrategyCreateSerializer,
)

from .models import ResearchRun
from .serializers import ScreenConditionSerializer

SCREEN_DEFAULTS = {'timeframe': CandleTimeframe.D1, 'logical_operator': LogicalOperator.AND}
MAX_SCREEN_CONDITIONS = 12


def json_data(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def validate_screen_condition(data):
    if not isinstance(data, dict):
        raise ValidationError("Each rule must be an object.")
    serializer = ScreenConditionSerializer(data=data)
    unknown = set(data) - set(serializer.fields)
    if unknown:
        raise ValidationError(f"Unsupported rule fields: {', '.join(sorted(unknown))}.")
    serializer.is_valid(raise_exception=True)
    result = serializer.validated_data
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


def validate_draft(draft, instrument_ids):
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
    serializer.is_valid(raise_exception=True)
    try:
        document = validate_definition(document_from_snapshot(draft))
    except (ValueError, KeyError) as exc:
        raise ValidationError(f'Invalid Studio draft: {exc}') from None
    watches = document['watchlist_instruments']
    ids = {item['instrument_id'] for item in watches} | {item['signal_instrument_id'] for item in watches}
    if not ids or ids - set(instrument_ids):
        raise ValidationError('Choose signal and traded instruments from this research context.')
    if Instrument.objects.filter(pk__in=ids, is_active=True).count() != len(ids):
        raise ValidationError('Choose active instruments for a new draft.')
    groups = [group for group in document['rule_groups'] if group.get('is_active', True)]
    if not any(group['rule_type'] == RuleType.ENTRY for group in groups):
        raise ValidationError('A strategy needs an entry condition.')
    if not any(group['rule_type'] != RuleType.ENTRY for group in groups):
        raise ValidationError('Add an exit, stop-loss or target condition.')
    strategy = Strategy(**serializer.validated_data, definition=document)
    result = {**{key: getattr(strategy, key) for key in base_fields}, **document}
    # Compilation validates source clocks, formula dependencies and risk units.
    try:
        compile_preview(strategy, document)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
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
    def numeric_parameters(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from numeric_parameters(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from numeric_parameters(child, (*path, index))
        elif path and path[-1] in {'value', 'period', 'length', 'fast', 'slow', 'signal', 'bars', 'count',
                                    'expires_after_bars', 'fixed_quantity', 'capital_percentage'}:
            try:
                yield path, float(value)
            except (ValueError, TypeError):
                pass
    previous = dict(numeric_parameters(baseline))
    for path, number in numeric_parameters(draft):
        if previous.get(path) != number and number not in numeric_choices:
            raise ValidationError('A trading threshold, period or sizing value was not supplied by the customer. Ask for that choice before generating rules.')


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
    timeframe = arguments.get("timeframe", SCREEN_DEFAULTS['timeframe'])
    operator = arguments.get("logical_operator", SCREEN_DEFAULTS['logical_operator'])
    conditions = arguments.get("conditions", [])
    if timeframe not in CandleTimeframe.values or operator not in LogicalOperator.values:
        raise ValidationError("Choose a supported timeframe and group operator.")
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= MAX_SCREEN_CONDITIONS:
        raise ValidationError(f"Provide between 1 and {MAX_SCREEN_CONDITIONS} screening conditions.")
    rules = [validate_screen_condition(value) for value in conditions]
    if any(not rule["is_active"] for rule in rules):
        raise ValidationError("Screening conditions must be active.")
    return {
        "time_rule": {"candle_timeframe": timeframe},
        "rule_groups": [{"rule_type": "ENTRY", "logical_operator": operator, "rules": rules}],
    }
