from celery import shared_task
from django.core.management import call_command


@shared_task(name="instruments.sync_fyers_master")
def sync_fyers_master():
    """Refresh instrument masters without changing unrelated segments on failure."""
    call_command("sync_instruments", archive_stale=True)
