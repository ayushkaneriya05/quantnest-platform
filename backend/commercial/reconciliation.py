"""Read-only provider reconciliation resolves uncertain checkout creation."""
from datetime import timedelta
from urllib.parse import urlencode

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PaymentAttempt, RenewalTerms, Subscription, PriceMapping
from .billing import verify_payment, record_refund, parse_provider_timestamp
from .provider import request_razorpay, ProviderUnavailable
from .usage import reject_request


def link_provider_checkout(attempt, remote_id):
    kind = "subscriptions" if attempt.kind == "subscription" else "orders"
    data = request_razorpay("GET", kind+"/"+remote_id)
    notes = data.get("notes") or {}
    if not isinstance(notes, dict) or notes.get("quantnest_attempt") != str(attempt.pk):
        reject_request("remote_checkout_mismatch", "The provider resource is not linked to this checkout request.")
    if kind == "orders" and (data.get("amount") != attempt.total_minor or data.get("currency") != attempt.currency):
        reject_request("remote_checkout_mismatch", "The provider order has different approved terms.")
    if kind == "subscriptions":
        mapping = PriceMapping.objects.filter(catalog=attempt.catalog, plan=attempt.plan,
            total_minor=attempt.total_minor, provider_plan_id=data.get("plan_id")).first()
        plan = request_razorpay("GET", "plans/" + mapping.provider_plan_id) if mapping else {}
        item = plan.get("item", {})
        if (not mapping or item.get("amount") != attempt.total_minor or item.get("currency") != attempt.currency
                or plan.get("period") != "monthly" or plan.get("interval") != 1 or data.get("quantity") != 1):
            reject_request("remote_checkout_mismatch", "The provider subscription has different approved terms.")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=attempt.user_id)
        row = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        field = "provider_subscription_id" if kind == "subscriptions" else "provider_order_id"
        previous = getattr(row, field)
        if previous and previous != remote_id:
            reject_request("remote_checkout_conflict", "A different remote resource is already linked.")
        if not previous:
            setattr(row, field, remote_id)
            row.status, row.error_code = "pending", ""
            row.save(update_fields=[field, "status", "error_code", "updated_at"])
    return row


def find_provider_checkout(attempt):
    """Discover by saved identity, never by user email, approximate amount or latest row."""
    kind = "subscriptions" if attempt.kind == "subscription" else "orders"
    query = {"count": 100}
    if kind == "orders":
        query["receipt"] = str(attempt.pk)
    else:
        query.update({"from": int((attempt.created_at-timedelta(minutes=2)).timestamp()),
            "to": int((attempt.created_at+timedelta(minutes=10)).timestamp())})
    matches = []
    for page in range(5):
        data = request_razorpay("GET", kind + "?" + urlencode({**query, "skip": page*100}))
        items = data.get("items", [])
        for row in items:
            notes = row.get("notes") or {}
            if isinstance(notes, dict) and notes.get("quantnest_attempt") == str(attempt.pk):
                matches.append(row["id"])
        if len(items) < 100:
            break
    else:
        # A truncated search cannot establish that there is only one matching resource.
        return None
    if len(matches) > 1:
        reject_request("remote_checkout_conflict", "More than one provider resource matches this request. A provider review is required.")
    return link_provider_checkout(attempt, matches[0]) if matches else None


def get_provider_refunds(payment_id):
    refunds = []
    for page in range(5):
        items = request_razorpay("GET", f"payments/{payment_id}/refunds?count=100&skip={page*100}").get("items", [])
        refunds.extend(items)
        if len(items) < 100:
            return refunds
    raise ProviderUnavailable("refund_history_limit")


def find_provider_refund(request):
    matches = [row for row in get_provider_refunds(request.payment.provider_id)
        if row.get("receipt") == f"qn-refund-{request.pk}"
        or isinstance(row.get("notes"), dict) and row["notes"].get("quantnest_refund") == str(request.pk)]
    if len(matches) > 1:
        reject_request("refund_conflict", "Multiple provider refunds require review before continuing.")
    return matches[0] if matches else None


def reconcile_payment_refunds(payment):
    if payment.applied_at:
        for refund in get_provider_refunds(payment.provider_id):
            record_refund(payment, refund)


def reconcile_checkout_attempt(attempt):
    if not attempt.provider_order_id and not attempt.provider_subscription_id:
        resolved = find_provider_checkout(attempt)
        if not resolved:
            PaymentAttempt.objects.filter(pk=attempt.pk).update(updated_at=timezone.now())
            return
        attempt = resolved
    if attempt.provider_order_id:
        payments = request_razorpay("GET", f"orders/{attempt.provider_order_id}/payments").get("items", [])
        for data in payments[:20]:
            payment = verify_payment(data["id"])
            reconcile_payment_refunds(payment)
    elif attempt.provider_subscription_id:
        state = request_razorpay("GET", "subscriptions/"+attempt.provider_subscription_id)
        subscription = Subscription.objects.filter(provider_id=attempt.provider_subscription_id).first()
        if subscription:
            subscription.cancel_at_end = state.get("status") in {"cancelled", "completed"} or bool(state.get("cancel_at_cycle_end"))
            subscription.save(update_fields=["cancel_at_end", "updated_at"])
            for change in RenewalTerms.objects.filter(subscription=subscription,
                    state__in=["preparing", "provider_unknown"], created_at__lt=timezone.now()-timedelta(minutes=2)).select_related("mapping"):
                matched = False
                if state.get("has_scheduled_changes"):
                    pending = request_razorpay("GET", f"subscriptions/{subscription.provider_id}/retrieve_scheduled_changes")
                    matched = pending.get("plan_id") == change.mapping.provider_plan_id
                else:
                    current_start = parse_provider_timestamp(state.get("current_start"))
                    matched = bool(state.get("plan_id") == change.mapping.provider_plan_id
                        and current_start and current_start >= change.effective_after)
                if matched:
                    RenewalTerms.objects.filter(pk=change.pk, state__in=["preparing", "provider_unknown"]).update(state="accepted")
                    Subscription.objects.filter(pk=subscription.pk).update(scheduled_plan=change.mapping.plan)
        invoices = request_razorpay("GET", f"invoices?subscription_id={attempt.provider_subscription_id}&count=100").get("items", [])
        for invoice in invoices:
            if invoice.get("payment_id"):
                reconcile_payment_refunds(verify_payment(invoice["payment_id"]))
    PaymentAttempt.objects.filter(pk=attempt.pk).update(updated_at=timezone.now())
