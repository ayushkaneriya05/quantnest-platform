"""Allowances checked once at user actions; final outcomes settle reservations.

catalog.ALLOWANCES defines each allowance. Inventory counts saved records,
per-request limits validate submitted size, and period credits reserve once.
Personal Private work has no commercial quotas or licence dependency.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone as utc
from math import ceil
from zoneinfo import ZoneInfo

from celery import current_app
from celery.signals import task_failure, task_postrun
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.exceptions import APIException

from execution.lifecycle import require_execution_scope
from .catalog import ALLOWANCES, get_active_catalog
from .models import Subscription, UsageBucket, UsageReservation

PAPER_CAPACITY_STATUSES = ("RUNNING", "PAUSED", "STOPPING", "ERROR")
FINAL_WORK_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}
logger = logging.getLogger(__name__)


class CommercialRestriction(APIException):
    status_code = 403
    default_code = "commercial_restriction"


def reject_request(code, message, **details):
    raise CommercialRestriction({"code": code, "message": message, **details})


def hash_payload(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# 1. One account policy supplies every allowance kind and Billing.
def get_account_policy(user, now=None):
    mode = settings.QUANTNEST_DEPLOYMENT_MODE
    now = now or timezone.now()
    subscription = catalog = start = end = None
    if mode == "private":
        plan = {"code": "private", "name": "Private", "price_minor": None,
                "limits": {key: None for key in ALLOWANCES}}
    else:
        subscription = Subscription.objects.filter(user=user).select_related("catalog").first()
        if subscription and subscription.paid_through and subscription.paid_through > now and subscription.status not in {"refunded", "disputed"}:
            catalog = subscription.catalog
            plan = catalog.specification["plans"][subscription.plan]
            start, end = subscription.period_start, subscription.paid_through
        else:
            catalog = get_active_catalog()
            plan = catalog.specification["plans"]["explore"]
            local = now.astimezone(ZoneInfo("Asia/Kolkata"))
            start = datetime(local.year, local.month, 1, tzinfo=local.tzinfo)
            start, end = start.astimezone(utc.utc), (start + relativedelta(months=1)).astimezone(utc.utc)
    return {"user_id": user.pk, "deployment_mode": mode, "limits_enforced": mode == "public",
            "record_usage": mode != "private", "plan": plan, "catalog": catalog, "subscription": subscription,
            "period_start": start, "period_end": end,
            "limits": {key: plan["limits"].get(key, 0) if mode == "public" else None for key in ALLOWANCES}}


def _prepare_allowance(user, kind, amounts, policy):
    """All three kinds validate inputs and account through this path.

    Reuse the returned policy only within the same action/outer transaction.
    """
    for feature, amount in amounts.items():
        if feature not in ALLOWANCES or ALLOWANCES[feature]["kind"] != kind:
            raise ValueError(f"Expected a {kind} allowance: {feature}")
        if type(amount) is not int or amount < (1 if kind == "period" else 0):
            raise ValueError(f"Invalid amount for allowance: {feature}")
    if policy is None:
        owner = get_user_model().objects.select_for_update().get(pk=user.pk)
        if not owner.is_active:
            reject_request("account_inactive", "This account cannot start new work.")
        return get_account_policy(owner)
    if policy["user_id"] != user.pk:
        raise ValueError("An allowance policy belongs to one account")
    return policy


def _check_limits(policy, amounts):
    for feature, requested in amounts.items():
        maximum = policy["limits"][feature]
        if maximum is not None and requested > maximum:
            code = {"inventory": "inventory_limit", "per_request": "request_limit", "period": "allowance_exhausted"}[ALLOWANCES[feature]["kind"]]
            reject_request(code, "This request exceeds your plan allowance. Existing results remain available.",
                           feature=feature, limit=maximum, requested=requested)


# 2. Inventory: count saved/deployed resources before changing them.
def _get_saved_resource_count(user, feature):
    definition = ALLOWANCES[feature]
    return apps.get_model(definition["model"]).objects.filter(user=user, **definition.get("filters", {})).count()


def _get_paper_usage(user, *, exclude_session=None, allocation=None, snapshot=None):
    """Shared counter for Billing and proposed Paper changes; no access checks."""
    from paper_trading.models import PaperTradingSession
    sessions = PaperTradingSession.objects.filter(user=user, status__in=PAPER_CAPACITY_STATUSES).select_related("allocation__deployed_version")
    if exclude_session:
        sessions = sessions.exclude(pk=exclude_session)
    rows = list(sessions)
    count = 0
    for row in rows:
        config = snapshot if allocation and row.allocation_id == allocation.pk else None
        if config is None and row.allocation_id and row.allocation.deployed_version_id:
            config = row.allocation.deployed_version.config_snapshot
        count += len((config or {}).get("watchlist_instruments", []))
    return {"paper_deployments": len(rows), "paper_instruments": count}


@transaction.atomic
def require_inventory_capacity(user, *, paper_snapshot=None, paper_session_id=None, paper_allocation=None, policy=None, **additions):
    """Check saved-item additions or a proposed Paper deploy/resume/version."""
    policy = _prepare_allowance(user, "inventory", additions, policy)
    if paper_snapshot is not None:
        require_execution_scope("paper")
    totals = {}
    if policy["limits_enforced"]:
        totals = {key: _get_saved_resource_count(user, key) + amount for key, amount in additions.items()}
        if paper_snapshot is not None and paper_allocation:
            from paper_trading.models import PaperTradingSession
            if not PaperTradingSession.objects.filter(user=user, allocation=paper_allocation, status__in=PAPER_CAPACITY_STATUSES).exists():
                paper_snapshot = None  # An inactive allocation uses no deployed capacity.
        if paper_snapshot is not None:
            paper = _get_paper_usage(user, exclude_session=paper_session_id, allocation=paper_allocation, snapshot=paper_snapshot)
            if paper_allocation is None:
                paper["paper_deployments"] += 1
                paper["paper_instruments"] += len(paper_snapshot.get("watchlist_instruments", []))
            totals.update(paper)
    _check_limits(policy, totals)
    return policy


# 3. Request sizes: validate the submitted totals without reserving usage.
@transaction.atomic
def require_request_limits(user, *, policy=None, **sizes):
    policy = _prepare_allowance(user, "per_request", sizes, policy)
    _check_limits(policy, sizes)
    return policy


# Backtest pricing belongs to allowance admission, not its serializer or engine.
def estimate_backtest_workload(user, config, start_date, end_date, *, policy=None):
    from backtesting.services import estimate_source_workload
    policy = policy if policy is not None else get_account_policy(user)
    preview = estimate_source_workload(config, start_date, end_date)
    _check_limits(policy, {"backtest_workload": preview["instrument_candles"]})
    if policy["record_usage"]:
        unit = policy["catalog"].specification["credit_candles"]
        preview.update(credits=max(1, ceil(preview["instrument_candles"] / unit)), credit_candles=unit,
                       definition=f"One credit per {unit:,} source candles including warmup. The reviewed cost is charged once on success.")
    else:
        preview.update(credits=None, credit_candles=None,
                       definition="Personal Private has no commercial usage quotas. Server capacity and execution controls still apply.")
    preview["config_hash"] = hash_payload(config)
    return {**preview, "token": signing.dumps({"user": user.pk, **preview}, salt="backtest-workload")}


# 4. Period credits: one entry point for fixed units and workload-priced credits.
@transaction.atomic
def reserve_usage(user, feature, key, payload, *, resource, amount=1, estimate_token="", policy=None):
    """Price, check and reserve any period allowance before queueing its resource.

    Source-candle pricing uses payload['config'], resource dates and the reviewed
    estimate token. Reported-token allowances reserve zero and settle actual usage
    after a successful answer. Fixed allowances reserve the submitted amount.
    Keep resource creation and this call inside the same outer transaction.
    """
    policy = _prepare_allowance(user, "period", {feature: amount}, policy)
    if not policy["record_usage"]:
        return None
    if not isinstance(key, str) or not key or len(key) > 160:
        reject_request("idempotency_required", "Provide an Idempotency-Key of up to 160 characters.")
    definition = ALLOWANCES[feature]
    postpaid = definition.get("pricing") == "reported_tokens"
    if postpaid:
        amount = 0  # Admission anchors the period; the answer's actual usage settles later.
    if definition.get("pricing") == "source_candles":
        config = payload["config"]
        if policy["limits_enforced"]:
            try:
                preview = signing.loads(estimate_token, salt="backtest-workload", max_age=1800)
            except signing.BadSignature:
                reject_request("estimate_required", "Review a fresh workload and credit estimate before starting.")
            if (preview["user"] != user.pk or preview["config_hash"] != hash_payload(config) or
                preview["start_date"] != resource.start_date.isoformat() or preview["end_date"] != resource.end_date.isoformat() or
                preview.get("credit_candles") != policy["catalog"].specification["credit_candles"]):
                reject_request("estimate_changed", "The strategy, dates or credit terms changed. Review a new estimate.")
            require_request_limits(user, policy=policy, backtest_workload=preview["instrument_candles"])
        else:
            preview = estimate_backtest_workload(user, config, resource.start_date, resource.end_date, policy=policy)
        amount = preview["credits"]
    payload = json.loads(json.dumps(payload, cls=DjangoJSONEncoder))
    fingerprint = hash_payload({"feature": feature, "amount": amount, "payload": payload})
    existing = UsageReservation.objects.filter(user=user, idempotency_key=key).first()
    if existing:
        if (existing.request_hash != fingerprint or existing.resource_type != definition["resource_type"] or
            existing.resource_id != str(resource.pk)):
            reject_request("idempotency_conflict", "This request key was already used with different inputs.")
        return existing
    start, end = policy["period_start"], policy["period_end"]
    maximum = policy["plan"]["limits"].get(feature, 0)
    bucket, _ = UsageBucket.objects.get_or_create(user=user, feature=feature, period_start=start,
        defaults={"period_end": end, "limit": maximum})
    _check_limits(policy, {feature: bucket.used + bucket.reserved + (1 if postpaid else amount)})
    bucket.limit, bucket.period_end, bucket.reserved = maximum, end, bucket.reserved + amount
    bucket.save(update_fields=["limit", "period_end", "reserved"])
    return UsageReservation.objects.create(bucket=bucket, user=user, idempotency_key=key,
        request_hash=fingerprint, amount=amount, resource_type=definition["resource_type"], resource_id=str(resource.pk))


@transaction.atomic
def settle_usage(reservation, *, failed=False, actual_amount=None):
    get_user_model().objects.select_for_update().get(pk=reservation.user_id)
    reservation = UsageReservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.state != "reserved":
        return
    amount = 0 if failed else reservation.amount if actual_amount is None else actual_amount
    if type(amount) is not int or amount < 0:
        raise ValueError("Settled usage must be a non-negative integer")
    UsageBucket.objects.filter(pk=reservation.bucket_id).update(
        reserved=F("reserved") - reservation.amount, used=F("used") + amount)
    reservation.amount = amount
    reservation.state = "refunded" if failed else "settled"
    reservation.completed_at = timezone.now()
    reservation.save(update_fields=["amount", "state", "completed_at"])


def complete_usage(kind, pk, status):
    """Only final outcomes settle accounting; duplicate completion is harmless."""
    if status not in FINAL_WORK_STATUSES:
        return
    row = UsageReservation.objects.filter(resource_type=kind, resource_id=str(pk), state="reserved").first()
    if row:
        amount = None
        if status == "COMPLETED" and row.bucket.feature == "research_tokens":
            usage = apps.get_model("research.ResearchRun").objects.values_list("usage", flat=True).get(pk=pk)
            amount = usage.get("total_tokens", 0)
        settle_usage(row, failed=status != "COMPLETED", actual_amount=amount)


# 5. Billing always returns the same allowance definitions. Unmetered counts are null.
def get_account_usage(user, *, policy=None):
    policy = policy or get_account_policy(user)
    terms, subscription = policy["plan"], policy["subscription"]
    start, end = policy["period_start"], policy["period_end"]
    usage = {
        key: {"limit": terms["limits"].get(key, 0), "kind": definition["kind"], "used": None, "reserved": 0,
              "display_divisor": definition.get("display_divisor", 1)}
        for key, definition in ALLOWANCES.items()
    }
    if policy["record_usage"]:
        buckets = {row.feature: row for row in UsageBucket.objects.filter(user=user, period_start=start)}
        counts = {key: _get_saved_resource_count(user, key) for key, definition in ALLOWANCES.items()
                  if definition["kind"] == "inventory" and "model" in definition}
        counts.update(_get_paper_usage(user))
        for key, definition in ALLOWANCES.items():
            kind, bucket = definition["kind"], buckets.get(key)
            item = usage[key]
            item["used"] = counts.get(key, 0)
            if kind == "period" and bucket:
                item.update(used=bucket.used, reserved=bucket.reserved)
    return {"plan": terms, "deployment_mode": policy["deployment_mode"], "limits_enforced": policy["limits_enforced"],
            "catalog_revision": policy["catalog"].revision if policy["catalog"] else None,
            "period_start": start, "period_end": end, "usage": usage,
            "renewal": {"automatic": bool(subscription and subscription.provider_id and not subscription.cancel_at_end),
                        "scheduled_plan": subscription.scheduled_plan if subscription else ""}}


# 6. Final outcomes settle existing reservations; they never check admission.
# Task dispatch, reservation links and completion share the catalog definitions.
COMPUTE_RESOURCES = {definition["task"]: (definition["resource_type"], definition["model"])
                     for definition in ALLOWANCES.values() if definition["kind"] == "period"}


def complete_compute_work(task_name, pk, *, failed=False, finished=True):
    resource = COMPUTE_RESOURCES.get(task_name)
    if not resource:
        return
    kind, model_name = resource
    jobs = apps.get_model(model_name).objects.filter(pk=pk)
    if failed:
        jobs.exclude(status__in=FINAL_WORK_STATUSES).update(
            status="FAILED", completed_at=timezone.now(), error_message="The background task could not complete. Its usage allowance was restored.")
    status = jobs.values_list("status", flat=True).first()
    if finished and status in FINAL_WORK_STATUSES:
        jobs.filter(completed_at__isnull=True).update(completed_at=timezone.now())
    complete_usage(kind, pk, status or "CANCELLED")


def queue_compute_work(task_name, pk):
    """Submit after commit; refund unstarted work if publication fails."""
    model = apps.get_model(COMPUTE_RESOURCES[task_name][1])

    def submit():
        try:
            current_app.send_task(task_name, args=[pk], queue="compute")
        except Exception as exc:
            logger.exception("Could not submit %s for resource %s", task_name, pk)
            with transaction.atomic():
                if model.objects.select_for_update().filter(pk=pk, status__in=["PENDING", "QUEUED"]).exists():
                    complete_compute_work(task_name, pk, failed=True)
            error = APIException("The compute queue is unavailable. Check this request's status before submitting a new run.",
                                 code="compute_queue_unavailable")
            error.status_code = 503
            raise error from exc

    transaction.on_commit(submit)


def handle_saved_work_outcome(sender, instance, update_fields=None, **kwargs):
    if update_fields is not None and "status" not in update_fields:
        return
    if instance.status not in FINAL_WORK_STATUSES:
        return
    task_name = next(name for name, resource in COMPUTE_RESOURCES.items() if resource[1] == sender._meta.label)

    def complete_after_commit():
        try:
            complete_compute_work(task_name, instance.pk, finished=False)
        except Exception:
            logger.exception("Could not settle saved outcome for %s %s", task_name, instance.pk)

    transaction.on_commit(complete_after_commit)


for task_name, (_, model_name) in COMPUTE_RESOURCES.items():
    post_save.connect(handle_saved_work_outcome, sender=model_name, dispatch_uid=f"usage-completion:{task_name}")


@receiver(task_postrun)
@receiver(task_failure)
def handle_task_outcome(sender=None, args=None, kwargs=None, state=None, exception=None, retval=None, **extra):
    task_name = getattr(sender, "name", "")
    if task_name not in COMPUTE_RESOURCES or (exception is None and state not in {"SUCCESS", "FAILURE"}):
        return
    pk = args[0] if args else (kwargs or {}).get("run_id", (kwargs or {}).get("mc_id"))
    if pk is None:
        return
    try:
        failed = exception is not None or state == "FAILURE"
        complete_compute_work(task_name, pk, failed=failed, finished=failed or retval is not None)
    except Exception:
        logger.exception("Could not settle completed task %s for resource %s", task_name, pk)
