import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


from django.core.cache import cache
from .models import Instrument

@shared_task(name="instruments.sync_fyers_master")
def sync_fyers_master():
    logger.info("Starting scheduled Fyers instrument master sync")
    try:
        call_command("sync_instruments", delete_stale=True)
    except Exception as e:
        logger.error(f"Failed to sync instruments: {e}")
        return {"status": "error", "message": str(e)}

    # Audit the sync
    active_count = Instrument.objects.filter(is_active=True).count()
    total_count = Instrument.objects.count()
    
    if total_count > 0:
        active_percentage = (active_count / total_count) * 100
    else:
        active_percentage = 0
        
    logger.info(f"Finished scheduled Fyers instrument master sync. Active: {active_count}/{total_count} ({active_percentage:.2f}%)")
    
    # If less than 10000 instruments are active, we probably got a bad file. Protect live trading.
    if active_count < 10000 and total_count > 20000:
        logger.critical(f"CRITICAL: Only {active_count} active instruments found after sync. This indicates a malformed master file. Disabling all derivatives.")
        Instrument.objects.filter(instrument_type__in=['FUTURE', 'OPTION']).update(is_active=False)
        cache.set("master_sync_status", "CRITICAL_FAILURE", timeout=86400)
        return {"status": "critical_failure", "active_count": active_count}
        
    cache.set("master_sync_status", "SUCCESS", timeout=86400)
    cache.set("master_sync_active_count", active_count, timeout=86400)

    return {"status": "ok", "active_count": active_count}
