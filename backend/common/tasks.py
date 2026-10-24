from datetime import timedelta

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone


@shared_task(name="common.sync_market_holidays")
def sync_market_holidays():
    """Daily sync of exchange holiday calendars."""
    call_command("sync_market_holidays")


@shared_task(name="common.prune_execution_commands")
def prune_execution_commands():
    """Bound command history; never remove pending work or financial checkpoints."""
    from execution.models import Command
    cutoff = timezone.now() - timedelta(days=7)
    ids = list(Command.objects.filter(applied_at__lt=cutoff).order_by('pk').values_list('pk', flat=True)[:10000])
    deleted, _ = Command.objects.filter(pk__in=ids).delete()
    return {'completed_commands_removed': deleted}
