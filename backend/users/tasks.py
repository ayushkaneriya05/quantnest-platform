from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

from .models import UserSession


@shared_task(name="users.cleanup_expired_sessions")
def cleanup_expired_sessions():
    count = UserSession.objects.filter(expires_at__lte=timezone.now()).count()
    UserSession.objects.filter(expires_at__lte=timezone.now()).delete()
    call_command("flushexpiredtokens", verbosity=0)
    return count
