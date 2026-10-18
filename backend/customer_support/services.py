"""Customer record linking, support email and milestone checkout workflows."""
from functools import partial
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from commercial.billing import require_verified_email, submit_checkout
from commercial.catalog import get_active_catalog
from commercial.models import PaymentAttempt
from commercial.usage import hash_payload, reject_request

from .models import Consent, Milestone, Ticket
from .tasks import send_support_email_task


def link_verified_customer_records(user):
    if EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        Ticket.objects.filter(user__isnull=True, email__iexact=user.email).update(user=user)
        Consent.objects.filter(user__isnull=True, email__iexact=user.email).update(user=user)


def queue_support_email(**message):
    transaction.on_commit(partial(send_support_email_task.delay, **message), robust=True)


def queue_ticket_acknowledgement(ticket):
    from .integrations import get_ticket_reply_address
    queue_support_email(to=ticket.email, subject=f"QuantNest request received: {ticket.subject}",
        reply_to=get_ticket_reply_address(ticket),
        body=f"We received your {ticket.get_request_type_display().lower()} request. Reference: {ticket.pk}.\nSupport hours: {settings.QUANTNEST_SUPPORT_HOURS}.\nPlease do not send passwords, broker tokens or API secrets.\n")


def create_milestone_checkout(user, milestone_id, data, key):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "private":
        reject_request("central_payment_required", "Project and installation payments are managed through your QuantNest customer account.")
    require_verified_email(user)
    if not settings.BILLING_ENABLED:
        reject_request("checkout_unavailable", "Merchant payments have not been activated.")
    if not key or len(key) > 160:
        reject_request("idempotency_required", "Provide a payment request identifier.")
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        milestone = get_object_or_404(Milestone.objects.select_for_update(of=("self",)).select_related(
            "quotation__engagement__ticket", "payment_attempt__catalog"), pk=milestone_id,
            quotation__engagement__ticket__user=user)
        if not milestone.approved_for_payment or not milestone.quotation.accepted_at or milestone.paid_at:
            reject_request("milestone_not_payable", "This milestone is not an accepted, staff-approved unpaid payment.")
        if data.get("approved_total_minor") != milestone.amount_minor:
            reject_request("milestone_total_changed", "Review the staff-approved milestone total before payment.")
        fingerprint = hash_payload({"milestone": milestone.pk, "amount": milestone.amount_minor})
        previous = PaymentAttempt.objects.filter(user=user, idempotency_key=key).first()
        if previous and previous.request_hash != fingerprint:
            reject_request("idempotency_conflict", "This payment request identifier has different inputs.")
        if milestone.payment_attempt_id:
            return milestone.payment_attempt
        kind = "private" if milestone.quotation.engagement.ticket.request_type == "private" else "project"
        attempt = PaymentAttempt.objects.create(user=user, idempotency_key=key, request_hash=fingerprint,
            catalog=get_active_catalog(), plan="private" if kind == "private" else "custom", kind=kind,
            base_minor=milestone.amount_minor, total_minor=milestone.amount_minor, currency=milestone.quotation.currency, status="creating")
        milestone.payment_attempt = attempt
        milestone.save(update_fields=["payment_attempt"])
    return submit_checkout(attempt, notes={"milestone": str(milestone_id)})
