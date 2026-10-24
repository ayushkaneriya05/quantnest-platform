"""Customer record linking and support email."""
from functools import partial
from allauth.account.models import EmailAddress
from django.conf import settings
from django.db import transaction

from .models import Ticket
from .tasks import send_support_email_task


def link_verified_customer_records(user):
    if EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        Ticket.objects.filter(user__isnull=True, email__iexact=user.email).update(user=user)


def queue_support_email(**message):
    transaction.on_commit(partial(send_support_email_task.delay, **message), robust=True)


def queue_ticket_acknowledgement(ticket):
    queue_support_email(to=ticket.email, subject=f"QuantNest request received: {ticket.subject}",
        body=f"We received your {ticket.get_request_type_display().lower()} request. Reference: {ticket.pk}.\nSupport hours: {settings.QUANTNEST_SUPPORT_HOURS}.\nPlease do not send passwords, broker tokens or API secrets.\n")
