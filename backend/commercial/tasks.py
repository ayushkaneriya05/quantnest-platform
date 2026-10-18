from celery import shared_task
from django.utils import timezone
from .models import Subscription


@shared_task(name="commercial.process_refund", autoretry_for=(Exception,), retry_backoff=10,
             retry_backoff_max=600, max_retries=5)
def process_refund_task(refund_id):
    from .billing import process_approved_refund
    process_approved_refund(refund_id)


@shared_task(name="commercial.reconcile")
def reconcile_commercial_state_task():
    import time
    from datetime import timedelta
    from django.db.models import Q
    from .reconciliation import reconcile_checkout_attempt
    from .models import PaymentAttempt
    deadline = time.monotonic() + 120
    stale_creation = Q(status__in=["creating", "provider_unknown"], created_at__lt=timezone.now()-timedelta(minutes=2))
    for attempt in PaymentAttempt.objects.filter(Q(status__in=["pending", "captured"]) | stale_creation).order_by("updated_at")[:20]:
        if time.monotonic() > deadline:
            break
        try:
            reconcile_checkout_attempt(attempt)
        except Exception:
            PaymentAttempt.objects.filter(pk=attempt.pk).update(updated_at=timezone.now())
            continue
    return Subscription.objects.filter(paid_through__lte=timezone.now(), status="active").update(status="expired")
