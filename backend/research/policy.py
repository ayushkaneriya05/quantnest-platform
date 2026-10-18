"""Software-only validation in addition to provider instructions and action confirmation."""
import re
from rest_framework.exceptions import ValidationError
from django.conf import settings

UNSUPPORTED_CLAIMS = re.compile(
    r"\b(?:guaranteed|assured|risk[ -]free)\s+(?:profits?|returns?|income)|"
    r"\b(?:i recommend|you should|you must)\s+(?:buy|sell|invest|short)\b|"
    r"\b(?:(?:your|recommended|our) price target(?: is)?|target price is|suitable for your (?:portfolio|risk)|best stocks? to buy)\b", re.I)


def validate_written_result(result):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return
    text = "\n".join([result.get("answer", ""), *result.get("next_steps", []), *result.get("clarification_questions", [])])
    if UNSUPPORTED_CLAIMS.search(text):
        raise ValidationError("The response crossed the software-only boundary. Ask for an explanation of your own conditions or recorded results.")


def validate_customer_rules(run, draft):
    """A new draft must be traceable to explicit user-supplied trading choices."""
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return
    supplied = run.request.get("strategy_snapshot") or run.request.get("draft_context") or {}
    baseline = supplied.get("draft", supplied) if isinstance(supplied, dict) else {}
    from .models import ResearchRun
    prompts = [run.prompt, *ResearchRun.objects.filter(session_id=run.session_id, user_id=run.user_id,
        pk__lt=run.pk).order_by("-pk").values_list("prompt", flat=True)[:20]]
    text = " ".join(prompts).lower()
    groups = draft.get("rule_groups", [])
    choices_supplied = all(re.search(pattern, text) for pattern in
        (r"\b(?:entry|enter|buy|long|short)\b", r"\b(?:exit|close|sell)\b", r"\b(?:minute|hour|daily|day|weekly|1m|5m|15m|1h|1d|1w)\b", r"\b(?:quantity|shares|capital|sizing)\b"))
    if not baseline and (not groups or not choices_supplied):
        raise ValidationError("Ask the customer to specify entry, exit, timeframe and sizing choices before translating a new draft.")
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
                            raise ValidationError("A trading threshold or indicator period was not supplied by the customer. Ask for that choice before generating rules.")
