"""Run admission, state transitions, progress publication and credit settlement."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import ACTIVE_RUN_STATUSES, ResearchRun

logger = logging.getLogger(__name__)


def accept_run(user, data, raw_data):
    """Freeze owned context and admit one request before dispatching any work."""
    from commercial.usage import (
        hash_payload,
        queue_compute_work,
        reject_request,
        require_inventory_capacity,
        require_request_limits,
        reserve_usage,
    )
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    from rest_framework.exceptions import ValidationError

    from .context import SAVED_CONTEXT_FIELDS, resolve_context
    from .models import ResearchSession
    from .validation import json_data, screen_configuration

    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        previous = ResearchRun.objects.filter(user=user, request_id=data["request_id"]).first()
        if previous:
            if previous.request.get("_request_hash") != hash_payload(raw_data):
                reject_request(
                    "idempotency_conflict", "This research request identifier was already used with different inputs."
                )
            return previous, False
        if ResearchRun.objects.filter(user=user, status__in=ACTIVE_RUN_STATUSES).exists():
            raise ValidationError("Wait for your active research turn or cancel it before starting another.")
        session = get_object_or_404(ResearchSession, pk=data["session"], user=user) if data.get("session") else None
        context = resolve_context(user, data, session.context if session else None)
        context["refresh"] = data["refresh"]
        context["_request_hash"] = hash_payload(raw_data)

        policy = require_request_limits(
            user,
            research_instruments=len(context.get("instrument_ids", [])),
            backtest_attachments=len(context.get("backtest_ids", [])),
        )
        if data["mode"] == "SCREEN" and (not session or session.kind != "SCREEN"):
            require_inventory_capacity(user, policy=policy, saved_screens=1)
        feature = "screens" if data["mode"] == "SCREEN" else "research_tokens"
        if session:
            previous_draft = session.runs.filter(status="COMPLETED", result__has_key="draft").order_by("-id").first()
            if previous_draft:
                context["draft_context"] = {
                    "run_id": previous_draft.pk,
                    "evidence_id": previous_draft.result.get("draft_evidence_id"),
                    "draft": previous_draft.result["draft"],
                }
        if data["mode"] == "SCREEN":
            if not context["instrument_ids"]:
                raise ValidationError("Select a watchlist or stocks to screen.")
            screen = screen_configuration(data["screen"])
            group = screen["rule_groups"][0]
            context["screen"] = {
                "timeframe": screen["time_rule"]["candle_timeframe"],
                "logical_operator": group["logical_operator"],
                "conditions": group["rules"],
            }
            context["timeframe"] = context["screen"]["timeframe"]
        if not session:
            session = ResearchSession.objects.create(
                user=user,
                kind="SCREEN" if data["mode"] == "SCREEN" else "CHAT",
                title=(data.get("prompt") or "Market screen")[:160],
            )
        elif data["mode"] == "SCREEN" and session.kind != "SCREEN":
            session.kind = "SCREEN"
        run = ResearchRun.objects.create(
            session=session,
            user=user,
            request_id=data["request_id"],
            mode=data["mode"],
            prompt=data.get("prompt", ""),
            request=json_data(context),
            as_of=timezone.now(),
        )
        reserve_usage(
            user, feature, f"research:{data['request_id']}", {"request": raw_data}, resource=run, policy=policy
        )
        session.context = json_data({key: context[key] for key in SAVED_CONTEXT_FIELDS if key in context})
        session.save(update_fields=["context", "kind", "updated_at"])
        publish_run(run)
        queue_compute_work("research.start_research", run.pk)
    run.refresh_from_db()
    return run, True


@transaction.atomic
def complete_run(run_id, result, usage):
    """Persist answer, actions and charge together. Admission uses the same user lock."""
    from commercial.usage import complete_usage
    from django.utils import timezone

    from .models import ResearchAction
    from .validation import finalize_result

    user_id = ResearchRun.objects.values_list("user_id", flat=True).get(pk=run_id)
    get_user_model().objects.select_for_update().get(pk=user_id)
    run = ResearchRun.objects.select_for_update().get(pk=run_id)
    if run.status != ResearchRun.Status.RUNNING:
        return None
    result = finalize_result(run, result)
    from .actions import prepare_proposed_actions

    actions = prepare_proposed_actions(run, result)
    if run.mode == "RESEARCH":
        total = usage.get("total_tokens")
        complete = usage.get("complete") is True and type(total) is int and total >= 0
        usage = {**usage, "complete": complete, "total_tokens": total if type(total) is int and total >= 0 else 0}
        if not complete:
            logger.error("Incomplete AI usage accounting for research run=%s; settling only reported tokens", run_id)
    completed = update_active_run(
        run_id,
        status=ResearchRun.Status.COMPLETED,
        progress_message="Research complete",
        result=result,
        usage=usage,
        completed_at=timezone.now(),
    )
    ResearchAction.objects.bulk_create([ResearchAction(run=completed, **item) for item in actions])
    complete_usage("research", run_id, ResearchRun.Status.COMPLETED)
    return completed


def update_active_run(run_id, *, expected_status=None, **changes):
    with transaction.atomic():
        run = ResearchRun.objects.select_for_update().filter(pk=run_id).first()
        if not run or run.status not in ACTIVE_RUN_STATUSES:
            return None
        if expected_status is not None and run.status != expected_status:
            return None
        for key, value in changes.items():
            setattr(run, key, value)
        run.revision += 1
        run.save(update_fields=[*changes, "revision", "updated_at"])
        publish_run(run)
        return run


def publish_run(run):
    # Progress contains no accumulated artifacts. Clients fetch the new revision once complete.
    data = {
        key: getattr(run, key)
        for key in ("id", "session_id", "revision", "status", "progress_message", "error_message")
    }
    data["session"] = data.pop("session_id")
    user_id = run.user_id

    def send():
        try:
            async_to_sync(get_channel_layer().group_send)(
                f"research_{user_id}", {"type": "research.update", "data": {"type": "research.update", "run": data}}
            )
        except Exception:
            logger.exception("Could not broadcast research run %s", run.pk)

    transaction.on_commit(send)


def research_allowance(user):
    from commercial.catalog import TOKENS_PER_CREDIT
    from commercial.models import UsageBucket
    from commercial.usage import get_account_policy

    policy = get_account_policy(user)
    used = 0
    if policy["record_usage"]:
        used = (
            UsageBucket.objects.filter(user=user, feature="research_tokens", period_start=policy["period_start"])
            .values_list("used", flat=True)
            .first()
            or 0
        )
    maximum = policy["plan"]["limits"].get("research_tokens")
    return {
        "used": used,
        "limit": maximum,
        "remaining": None if maximum is None else max(0, maximum - used),
        "tokens_per_credit": TOKENS_PER_CREDIT,
        "enforced": policy["limits_enforced"],
        "period_end": policy["period_end"],
    }
