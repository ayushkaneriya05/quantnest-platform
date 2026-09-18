import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="common.sync_market_holidays")
def sync_market_holidays():
    """Daily sync of exchange holiday calendars."""
    logger.info("Starting scheduled market holiday sync")
    try:
        call_command("sync_market_holidays")
    except Exception as exc:
        logger.exception("Failed to sync market holidays: %s", exc)
        return {"status": "error", "message": str(exc)}

    logger.info("Finished scheduled market holiday sync")
    return {"status": "ok"}
