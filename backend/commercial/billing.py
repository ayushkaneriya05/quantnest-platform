"""Captured payments grant time once; provider callbacks never grant on their own."""
from datetime import datetime, timedelta, timezone as utc
import hmac
import hashlib
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from allauth.account.models import EmailAddress
from .models import PaymentAttempt, Payment, Subscription, Invoice, PriceMapping, RefundRequest, RenewalTerms, RefundRecord, Dispute
from .provider import request_razorpay, ProviderUnavailable
from .catalog import get_active_catalog
from .usage import hash_payload, reject_request


def parse_provider_timestamp(value):
    return datetime.fromtimestamp(int(value), utc.utc) if value else None


def require_verified_email(user):
    if not EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        reject_request("email_verification_required", "Verify your email before checkout.")


def calculate_billing_totals(catalog, plan, subscription=None):
    base = catalog.specification["plans"][plan]["price_minor"]
    protected = bool(subscription and subscription.plan == plan and subscription.founding_price_until and subscription.founding_price_until > timezone.now())
    if protected:
        base = min(base, subscription.protected_price_minor or base)
    tax = (base * settings.BILLING_TAX_BPS + 5000) // 10000
    return {"base_minor": base, "tax_minor": tax, "total_minor": base + tax,
        "price_protected_until": subscription.founding_price_until if protected else None}


def create_checkout(user, data, key, *, manual=False):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "private":
        reject_request("checkout_unavailable", "Personal Private does not use public subscription checkout.")
    require_verified_email(user)
    if not settings.BILLING_ENABLED:
        reject_request("checkout_unavailable", "Checkout is not open yet. You can use Explore or contact us.")
    catalog = get_active_catalog()
    if data.get("catalog_revision") != catalog.revision:
        reject_request("catalog_changed", "Review the current prices and terms before continuing.", revision=catalog.revision)
    plan = data.get("plan")
    if not isinstance(plan, str) or plan not in {"build", "pro"}:
        reject_request("invalid_plan", "Choose Build or Pro.")
    if not key or len(key) > 160:
        reject_request("idempotency_required", "Provide a unique request key.")
    if not manual and data.get("renewal_consent") is not True:
        reject_request("renewal_consent", "Confirm monthly automatic renewal or choose manual payment.")
    subscription = Subscription.objects.filter(user=user).first()
    reviewed = calculate_billing_totals(catalog, plan, subscription)
    base, tax, total = (reviewed[key] for key in ("base_minor", "tax_minor", "total_minor"))
    mapping = None
    if not manual:
        mapping = PriceMapping.objects.filter(catalog=catalog, plan=plan, total_minor=total, tax_bps=settings.BILLING_TAX_BPS).first()
        if mapping is None:
            reject_request("provider_price_unavailable", "Automatic renewal is not configured for this price. Choose manual payment or contact support.")
    if data.get("approved_total_minor") != total:
        reject_request("checkout_total_changed", "Review the updated total before paying.", base_minor=base, tax_minor=tax, total_minor=total)
    kind = "manual" if manual else "subscription"
    fingerprint = hash_payload({"plan": plan, "revision": catalog.revision, "kind": kind, "total": total})
    buyer = data.get("billing_details", {})
    if not isinstance(buyer, dict) or set(buyer) - {"name", "address", "tax_id"} or any(not isinstance(value, str) or len(value) > 500 for value in buyer.values()):
        reject_request("invalid_billing_details", "Enter a buyer name, address and optional tax identifier of up to 500 characters.")
    fingerprint = hash_payload({"terms": fingerprint, "buyer": buyer})
    if mapping:
        provider_plan = request_razorpay("GET", "plans/" + mapping.provider_plan_id)
        item = provider_plan.get("item", {})
        if item.get("amount") != total or item.get("currency") != "INR" or provider_plan.get("period") != "monthly" or provider_plan.get("interval") != 1:
            raise ProviderUnavailable("provider_price_mismatch")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        attempt = PaymentAttempt.objects.filter(user=user, idempotency_key=key).first()
        if attempt:
            if attempt.request_hash != fingerprint:
                reject_request("idempotency_conflict", "This checkout key was already used with different inputs.")
            return attempt
        unresolved = PaymentAttempt.objects.filter(user=user, kind__in=["manual", "subscription"], status__in=["creating", "pending", "provider_unknown"]).order_by("created_at").first()
        if unresolved:
            if unresolved.request_hash == fingerprint:
                return unresolved
            reject_request("checkout_pending", "Resolve your existing checkout before starting another payment.", attempt_id=str(unresolved.pk))
        if subscription and subscription.provider_id and not subscription.cancel_at_end and subscription.paid_through and subscription.paid_through > timezone.now():
            reject_request("subscription_active", "Schedule a plan change on your current subscription.")
        attempt = PaymentAttempt.objects.create(user=user, idempotency_key=key, request_hash=fingerprint,
            catalog=catalog, plan=plan, kind=kind, base_minor=base, tax_minor=tax, total_minor=total, status="creating", billing_details=buyer)
    return submit_checkout(attempt, provider_plan_id=mapping.provider_plan_id if mapping else None)


def submit_checkout(attempt, *, provider_plan_id=None, notes=None):
    """Submit a newly saved checkout once; retain uncertain provider outcomes."""
    notes = {**(notes or {}), "quantnest_attempt": str(attempt.pk)}
    if attempt.kind == "subscription":
        path, field = "subscriptions", "provider_subscription_id"
        payload = {"plan_id": provider_plan_id, "total_count": 120, "quantity": 1, "customer_notify": 1, "notes": notes}
    else:
        path, field = "orders", "provider_order_id"
        payload = {"amount": attempt.total_minor, "currency": attempt.currency, "receipt": str(attempt.pk), "notes": notes}
    try:
        result = request_razorpay("POST", path, payload)
        setattr(attempt, field, result["id"])
        attempt.status = "pending"
    except ProviderUnavailable as exc:
        # Creation may have succeeded remotely. Provider reconciliation must
        # resolve it; repeating this POST could create duplicate mandates/orders.
        attempt.status, attempt.error_code = "provider_unknown", str(exc)
    attempt.save(update_fields=[field, "status", "error_code", "updated_at"])
    return attempt


def get_checkout_data(attempt):
    return {"id": attempt.pk, "status": attempt.status, "plan": attempt.plan,
        "key_id": settings.RAZORPAY_KEY_ID, "order_id": attempt.provider_order_id,
        "subscription_id": attempt.provider_subscription_id, "base_minor": attempt.base_minor,
        "tax_minor": attempt.tax_minor, "total_minor": attempt.total_minor, "currency": attempt.currency,
        "catalog_revision": attempt.catalog.revision, "error_code": attempt.error_code}


def verify_payment(payment_id, *, user=None):
    payment_data = request_razorpay("GET", "payments/" + payment_id)
    order_id = payment_data.get("order_id")
    subscription_id = payment_data.get("subscription_id")
    invoice_data = {}
    if payment_data.get("invoice_id"):
        invoice_data = request_razorpay("GET", "invoices/" + payment_data["invoice_id"])
        subscription_id = invoice_data.get("subscription_id")
    attempt = PaymentAttempt.objects.filter(provider_subscription_id=subscription_id).first() if subscription_id else None
    if not attempt and order_id:
        attempt = PaymentAttempt.objects.filter(provider_order_id=order_id).first()
    if not attempt or (user and attempt.user_id != user.pk):
        reject_request("payment_not_owned", "This payment is not linked to your checkout.")
    existing = Payment.objects.filter(provider_id=payment_id, attempt=attempt, applied_at__isnull=False).first()
    if existing:
        return existing
    captured_payment = payment_data.get("status") == "captured" or (
        payment_data.get("status") == "refunded" and payment_data.get("captured") is True)
    refunds = []
    if captured_payment and (payment_data.get("amount_refunded", 0) or payment_data.get("status") == "refunded"):
        from .reconciliation import get_provider_refunds
        refunds = get_provider_refunds(payment_id)
    if payment_data.get("status") == "refunded" and (not captured_payment or sum(
            row.get("amount", 0) for row in refunds if row.get("status") == "processed") != payment_data.get("amount")):
        reject_request("refund_reconciliation_pending", "The provider refund history must be verified before this payment can be reconciled.")
    provider_subscription = request_razorpay("GET", "subscriptions/" + subscription_id) if subscription_id else None
    purchased_catalog, purchased_plan = attempt.catalog, attempt.plan
    base_minor, tax_minor, total_minor = attempt.base_minor, attempt.tax_minor, attempt.total_minor
    verified_start = verified_end = None
    if provider_subscription and captured_payment:
        verified_start, verified_end = parse_provider_timestamp(invoice_data.get("billing_start")), parse_provider_timestamp(invoice_data.get("billing_end"))
        if (invoice_data.get("subscription_id") != subscription_id or invoice_data.get("payment_id") != payment_id
                or invoice_data.get("status") != "paid" or not verified_start or not verified_end or verified_end <= verified_start):
            reject_request("billing_period_pending", "The captured payment is awaiting its own verified invoice period.")
        current = Subscription.objects.filter(user_id=attempt.user_id, provider_id=subscription_id).first()
        changed = RenewalTerms.objects.select_related("mapping__catalog").filter(subscription=current,
            state="accepted", effective_after__lte=verified_start).order_by("-effective_after", "-pk").first() if current else None
        if changed:
            purchased_catalog, purchased_plan = changed.mapping.catalog, changed.mapping.plan
            base_minor, tax_minor, total_minor = changed.base_minor, changed.tax_minor, changed.total_minor
    if payment_data.get("amount") != total_minor or payment_data.get("currency") != attempt.currency:
        reject_request("payment_amount_mismatch", "The verified payment does not match the approved total.")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=attempt.user_id)
        attempt = PaymentAttempt.objects.select_for_update().select_related("user", "catalog").get(pk=attempt.pk)
        payment, _ = Payment.objects.get_or_create(provider_id=payment_id,
            defaults={"attempt": attempt, "amount_minor": payment_data["amount"], "currency": payment_data["currency"], "status": payment_data["status"]})
        if payment.applied_at:
            # Captured access is never rolled back by a delayed authorized event.
            return payment
        payment.status = "captured" if captured_payment else payment_data["status"]
        payment.fee_minor = payment_data.get("fee") or 0
        if payment.status != "captured":
            payment.save(update_fields=["status", "fee_minor"])
            return payment
        now = timezone.now()
        # Historical non-subscription receipts cannot grant a workspace subscription.
        if attempt.kind not in {"manual", "subscription"}:
            payment.captured_at = now
            payment.applied_at = now
            payment.billing_snapshot = {"kind": attempt.kind, "base_minor": attempt.base_minor,
                "tax_minor": attempt.tax_minor, "total_minor": attempt.total_minor}
            payment.save()
            Invoice.objects.get_or_create(payment=payment, defaults={"number": f"QN-{payment.pk:010d}", "user": attempt.user,
                "snapshot": {"seller": settings.QUANTNEST_LEGAL_NAME, "buyer_email": attempt.user.email,
                    "kind": attempt.kind, "base_minor": attempt.base_minor, "tax_minor": attempt.tax_minor,
                    "total_minor": attempt.total_minor, "currency": attempt.currency}})
            attempt.status = "captured"
            attempt.save(update_fields=["status", "updated_at"])
            for refund in refunds:
                record_refund(payment, refund)
            if refunds:
                payment.refresh_from_db(fields=["status"])
            return payment
        subscription, _ = Subscription.objects.get_or_create(user=attempt.user, defaults={"catalog": attempt.catalog})
        captured = parse_provider_timestamp(payment_data.get("captured_at")) or parse_provider_timestamp(invoice_data.get("paid_at")) or parse_provider_timestamp(payment_data.get("created_at")) or now
        if provider_subscription:
            start, end = verified_start, verified_end
        else:
            start = max(captured, subscription.paid_through or captured)
            end = start + relativedelta(months=1)
        payment.captured_at, payment.period_start, payment.period_end, payment.applied_at = captured, start, end, now
        payment.billing_snapshot = {"catalog": purchased_catalog.revision, "plan": purchased_plan,
            "base_minor": base_minor, "tax_minor": tax_minor, "total_minor": total_minor}
        payment.save()
        # A late older captured payment cannot shorten a newer paid period.
        if not subscription.paid_through or end > subscription.paid_through:
            subscription.plan, subscription.catalog = purchased_plan, purchased_catalog
            subscription.period_start, subscription.paid_through = start, end
            subscription.provider_id = subscription_id
            subscription.status = "active"
            if subscription.scheduled_plan == purchased_plan:
                subscription.scheduled_plan = ""
            if subscription.founding_price_until is None:
                subscription.founding_price_until = captured + relativedelta(months=6)
                subscription.protected_price_minor = base_minor
            subscription.save()
        attempt.status = "captured"
        attempt.save(update_fields=["status", "updated_at"])
        Invoice.objects.get_or_create(payment=payment, defaults={"number": f"QN-{payment.pk:010d}", "user": attempt.user,
            "snapshot": {"seller": settings.QUANTNEST_LEGAL_NAME, "seller_tax_id": settings.BILLING_TAX_ID,
                "buyer_email": attempt.user.email, "buyer": attempt.billing_details, "plan": purchased_plan, "catalog": purchased_catalog.revision,
                "base_minor": base_minor, "tax_minor": tax_minor, "total_minor": total_minor,
                "currency": attempt.currency, "period_start": start.isoformat(), "period_end": end.isoformat()}})
        for refund in refunds:
            record_refund(payment, refund)
        if refunds:
            payment.refresh_from_db(fields=["status"])
        return payment


def process_payment_webhook(payload):
    """Verify provider state and apply it directly; payment IDs prevent double credit."""
    event_type = payload["event"]
    entities = payload.get("payload", {})
    payment = entities.get("payment", {}).get("entity", {})
    refund = entities.get("refund", {}).get("entity", {})
    dispute = entities.get("dispute", {}).get("entity", {})
    payment_id = payment.get("id") or refund.get("payment_id") or dispute.get("payment_id")
    if payment_id:
        verified = verify_payment(payment_id)
        if event_type.startswith("refund."):
            if refund.get("id"):
                verified_refund = request_razorpay("GET", f"payments/{verified.provider_id}/refunds/{refund['id']}")
                record_refund(verified, verified_refund)
                request = RefundRequest.objects.filter(payment=verified, provider_id=verified_refund["id"]).first()
                if request:
                    apply_verified_refund(request, verified_refund)
        if event_type.startswith("payment.dispute.") and dispute.get("id"):
            record_dispute(verified, request_razorpay("GET", "disputes/" + dispute["id"]))
    subscription_data = entities.get("subscription", {}).get("entity", {})
    if subscription_data.get("id"):
        state = request_razorpay("GET", "subscriptions/" + subscription_data["id"])
        Subscription.objects.filter(provider_id=state["id"]).update(cancel_at_end=
            state.get("status") in {"cancelled", "completed"} or bool(state.get("cancel_at_cycle_end")))


def cancel_subscription_renewal(user):
    subscription = Subscription.objects.filter(user=user).first()
    if not subscription:
        reject_request("subscription_required", "There is no paid subscription to cancel.")
    if subscription.provider_id and not subscription.cancel_at_end:
        request_razorpay("POST", f"subscriptions/{subscription.provider_id}/cancel", {"cancel_at_cycle_end": 1})
    subscription.cancel_at_end = True
    subscription.scheduled_plan = ""
    subscription.save(update_fields=["cancel_at_end", "scheduled_plan", "updated_at"])
    return subscription


def schedule_plan_change(user, plan, approved_total=None):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "private":
        reject_request("checkout_unavailable", "Personal Private has no subscription or renewal.")
    if not isinstance(plan, str) or plan not in {"explore", "build", "pro"}:
        reject_request("invalid_plan", "Choose Explore, Build or Pro.")
    if plan == "explore":
        return cancel_subscription_renewal(user)
    subscription = Subscription.objects.select_related("catalog").filter(user=user).first()
    if not subscription or not subscription.provider_id or not subscription.paid_through:
        reject_request("automatic_subscription_required", "Choose a new plan through reviewed checkout for manual renewal.")
    if plan == subscription.plan and not subscription.scheduled_plan:
        return subscription
    catalog = get_active_catalog()
    reviewed = calculate_billing_totals(catalog, plan, subscription)
    base, total = reviewed["base_minor"], reviewed["total_minor"]
    if approved_total != total:
        reject_request("checkout_total_changed", "Review the renewal total before confirming.", total_minor=total)
    mapping = PriceMapping.objects.filter(catalog=catalog, plan=plan, total_minor=total).first()
    if not mapping:
        reject_request("provider_price_unavailable", "Automatic plan changes await an approved provider price mapping.")
    verified_plan = request_razorpay("GET", "plans/" + mapping.provider_plan_id)
    if verified_plan.get("item", {}).get("amount") != total or verified_plan.get("item", {}).get("currency") != "INR" or verified_plan.get("period") != "monthly" or verified_plan.get("interval") != 1:
        reject_request("provider_price_mismatch", "The provider plan does not match the reviewed price.")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if RenewalTerms.objects.filter(subscription=subscription, state__in=["preparing", "provider_unknown"]).exists():
            reject_request("provider_reconciliation_pending", "A previous plan change is awaiting provider reconciliation.")
        change = RenewalTerms.objects.create(subscription=subscription, mapping=mapping, effective_after=subscription.paid_through,
            base_minor=base, tax_minor=total-base, total_minor=total)
    try:
        request_razorpay("PATCH", f"subscriptions/{subscription.provider_id}", {"plan_id": mapping.provider_plan_id,
            "schedule_change_at": "cycle_end", "customer_notify": 1})
    except ProviderUnavailable:
        change.state = "provider_unknown"
        change.save(update_fields=["state"])
        raise
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        RenewalTerms.objects.filter(pk=change.pk).update(state="accepted")
        Subscription.objects.filter(pk=subscription.pk).update(scheduled_plan=plan)
    return Subscription.objects.get(pk=subscription.pk)


def request_refund(user, payment_id, reason):
    payment = Payment.objects.filter(provider_id=payment_id, attempt__user=user, status="captured").first()
    if not payment:
        reject_request("payment_not_owned", "Select one of your captured payments.")
    if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 3000:
        reject_request("refund_reason_required", "Describe the refund request in 5–3,000 characters.")
    first = Payment.objects.filter(attempt__user=user, attempt__kind__in=["subscription", "manual"], applied_at__isnull=False).order_by("captured_at", "pk").first()
    within_window = bool(payment.attempt.kind in {"subscription", "manual"} and first and first.pk == payment.pk and payment.captured_at and timezone.now() <= payment.captured_at + timedelta(days=7))
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        Payment.objects.select_for_update().get(pk=payment.pk)
        existing = RefundRequest.objects.filter(payment=payment).exclude(status="rejected").first()
        if existing:
            return existing
        from django.db.models import Sum
        refunded = RefundRecord.objects.filter(payment=payment).exclude(status="failed").aggregate(total=Sum("amount_minor"))["total"] or 0
        remaining = payment.amount_minor-refunded
        if remaining <= 0:
            reject_request("refund_already_pending", "This payment has already been refunded or has a pending refund.")
        return RefundRequest.objects.create(user=user, payment=payment, reason=reason,
            status="eligible" if within_window else "review", amount_minor=remaining)


@transaction.atomic
def apply_verified_refund(request, verified):
    get_user_model().objects.select_for_update().get(pk=request.user_id)
    request = RefundRequest.objects.select_for_update().select_related("payment__attempt").get(pk=request.pk)
    if (verified.get("payment_id") != request.payment.provider_id or verified.get("amount") != request.amount_minor
            or request.provider_id and request.provider_id != verified.get("id")):
        reject_request("refund_mismatch", "The provider refund does not match the approved request.")
    record_refund(request.payment, verified, refund_request=request)
    request.refresh_from_db()
    return request


def process_approved_refund(refund_id):
    """Persist a stable key before refunding; discover older uncertain calls by GET."""
    from .reconciliation import find_provider_refund
    request = RefundRequest.objects.select_related("payment").get(pk=refund_id)
    if request.status in {"processed", "failed", "rejected"}:
        return
    if request.provider_id:
        result = request_razorpay("GET", f"payments/{request.payment.provider_id}/refunds/{request.provider_id}")
    elif request.status != "approved" and not request.provider_idempotency_key:
        result = find_provider_refund(request)
        if not result:
            raise ProviderUnavailable("refund_reconciliation_pending")
    else:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user_id)
            request = RefundRequest.objects.select_for_update().select_related("payment").get(pk=request.pk)
            if request.status in {"processed", "failed", "rejected"}:
                return
            if request.status != "approved" and not request.provider_idempotency_key:
                raise ProviderUnavailable("refund_reconciliation_pending")
            if not request.provider_idempotency_key:
                request.provider_idempotency_key = f"quantnest-refund-{request.pk}"
            request.status = "provider_pending"
            request.save(update_fields=["status", "provider_idempotency_key"])
        result = request_razorpay("POST", f"payments/{request.payment.provider_id}/refund", {"amount": request.amount_minor,
            "receipt": f"qn-refund-{request.pk}", "notes": {"quantnest_refund": str(request.pk)}},
            headers={"X-Refund-Idempotency": request.provider_idempotency_key})
    apply_verified_refund(request, result)


@transaction.atomic
def refresh_subscription_access(payment):
    if payment.attempt.kind not in {"manual", "subscription"}:
        return
    latest = Payment.objects.filter(attempt__user_id=payment.attempt.user_id, attempt__kind__in=["manual", "subscription"],
        applied_at__isnull=False, status="captured", period_end__isnull=False).exclude(
        dispute__status__in=["open", "under_review", "lost"]).order_by("-period_end", "-pk").first()
    subscription = Subscription.objects.select_for_update().filter(user_id=payment.attempt.user_id).first()
    if subscription:
        if latest:
            subscription.period_start, subscription.paid_through = latest.period_start, latest.period_end
            subscription.plan = latest.billing_snapshot.get("plan", latest.attempt.plan)
            revision = latest.billing_snapshot.get("catalog", latest.attempt.catalog.revision)
            from .models import CatalogRevision
            subscription.catalog = CatalogRevision.objects.get(revision=revision)
            subscription.status = "active" if latest.period_end > timezone.now() else "expired"
        else:
            subscription.status = "disputed" if Dispute.objects.filter(payment=payment).exclude(status__in=["won", "closed"]).exists() else "refunded"
            subscription.paid_through = timezone.now()
        subscription.save()


@transaction.atomic
def record_refund(payment, data, *, refund_request=None):
    from django.db.models import Sum, Q
    get_user_model().objects.select_for_update().get(pk=payment.attempt.user_id)
    if data.get("payment_id") != payment.provider_id or type(data.get("amount")) is not int or not 0 < data["amount"] <= payment.amount_minor:
        reject_request("refund_mismatch", "The verified refund does not match this payment.")
    row, created = RefundRecord.objects.get_or_create(provider_id=data["id"], defaults={"payment": payment,
        "amount_minor": data["amount"], "status": data.get("status", "pending")})
    if row.payment_id != payment.pk or row.amount_minor != data["amount"]:
        reject_request("refund_conflict", "A provider refund identifier has conflicting payment data.")
    if row.status != "processed":
        row.status = data.get("status", "pending")
    if row.status == "processed" and not row.credit_note:
        row.credit_note = {"number": "QN-CN-"+str(row.pk), "invoice": payment.invoice.number, "amount_minor": row.amount_minor,
            "currency": payment.currency, "provider_refund_id": row.provider_id, "issued_at": parse_provider_timestamp(data.get("created_at")).isoformat() if data.get("created_at") else timezone.now().isoformat()}
    row.save()
    if refund_request is None:
        notes = data.get("notes") or {}
        identity = notes.get("quantnest_refund", "") if isinstance(notes, dict) else ""
        if not identity and str(data.get("receipt", "")).startswith("qn-refund-"):
            identity = str(data["receipt"]).removeprefix("qn-refund-")
        match = Q(provider_id=row.provider_id)
        if str(identity).isdigit():
            match |= Q(pk=int(identity), status__in=["approved", "provider_pending", "pending", "processed", "failed"])
        refund_request = RefundRequest.objects.select_for_update().filter(match, payment=payment).first()
    if refund_request:
        if refund_request.amount_minor != row.amount_minor or refund_request.provider_id and refund_request.provider_id != row.provider_id:
            reject_request("refund_conflict", "The verified refund conflicts with this approved request.")
        if refund_request.status != "processed":
            refund_request.status = row.status
        refund_request.provider_id, refund_request.credit_note = row.provider_id, row.credit_note
        refund_request.save(update_fields=["status", "provider_id", "credit_note"])
    refunded = RefundRecord.objects.filter(payment=payment, status="processed").aggregate(total=Sum("amount_minor"))["total"] or 0
    if refunded >= payment.amount_minor:
        changed = Payment.objects.filter(pk=payment.pk).exclude(status="refunded").update(status="refunded")
        if changed:
            refresh_subscription_access(payment)
    return row


@transaction.atomic
def record_dispute(payment, data):
    get_user_model().objects.select_for_update().get(pk=payment.attempt.user_id)
    if data.get("payment_id") != payment.provider_id or data.get("currency") != payment.currency:
        reject_request("dispute_mismatch", "The verified dispute does not match this payment.")
    values = {"payment_id": payment.pk, "status": data["status"], "amount_minor": data["amount"],
        "deducted_minor": data.get("amount_deducted", 0), "respond_by": parse_provider_timestamp(data.get("respond_by"))}
    previous = Dispute.objects.filter(provider_id=data["id"]).values(*values).first()
    if previous and previous["payment_id"] != payment.pk:
        reject_request("dispute_conflict", "This provider dispute belongs to a different payment.")
    if previous == values:
        return Dispute.objects.get(provider_id=data["id"])
    row, _ = Dispute.objects.update_or_create(provider_id=data["id"], defaults=values)
    refresh_subscription_access(payment)
    return row


def is_webhook_signature_valid(body, signature):
    secrets = [settings.RAZORPAY_WEBHOOK_SECRET, settings.RAZORPAY_PREVIOUS_WEBHOOK_SECRET]
    return any(secret and hmac.compare_digest(hmac.new(secret.encode(), body, hashlib.sha256).hexdigest().encode(), signature.encode()) for secret in secrets)
