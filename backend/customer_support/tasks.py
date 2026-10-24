"""Support messages and account-content erasure."""
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from research.models import ResearchRun
from .models import ErasureRequest, Ticket, Reply


@shared_task(name="customer_support.send_email", autoretry_for=(Exception,), retry_backoff=10,
             retry_backoff_max=600, max_retries=5)
def send_support_email_task(to, subject, body):
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to]).send(fail_silently=False)


@shared_task(name="customer_support.retention")
def prune_customer_data_task():
    now = timezone.now()
    completed = 0
    for request in ErasureRequest.objects.filter(completed_at__isnull=True).order_by("pk")[:20]:
        with transaction.atomic():
            from django.contrib.auth import get_user_model
            get_user_model().objects.select_for_update().get(pk=request.user_id)
            request = ErasureRequest.objects.select_for_update().get(pk=request.pk)
            if request.completed_at or ResearchRun.objects.filter(user_id=request.user_id, started_at__isnull=False, completed_at__isnull=True).exists():
                continue
            from research.models import ResearchSession
            from trade_journal.models import JournalEntry
            user = request.user
            if user.is_active:
                continue
            ResearchSession.objects.filter(user=user).delete()
            JournalEntry.objects.filter(user=user).update(title="", notes="", lessons_learned="", mistake_tags=[])
            tickets = Ticket.objects.filter(user=user).exclude(request_type__in=["private", "custom", "grievance", "security"])
            Reply.objects.filter(ticket__in=tickets).update(body="", author=None)
            tickets.update(email=user.email, subject="Deleted account request", body="", status="closed")
            request.completed_at = now
            request.save(update_fields=["completed_at"])
            completed += 1
    return {"erased_optional_content": completed}
