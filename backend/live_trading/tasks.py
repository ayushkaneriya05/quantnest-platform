import logging

from celery import shared_task

from .models import TradingSession
from .services import LiveExecutionService

logger = logging.getLogger(__name__)


@shared_task(name="live_trading.run_active_sessions")
def run_active_sessions(symbol=None):
    processed = 0
    for session in TradingSession.objects.filter(status="RUNNING").select_related("strategy", "broker_credential"):
        try:
            if LiveExecutionService.execute_session_once(session, symbol=symbol):
                processed += 1
        except Exception as exc:
            logger.exception(
                "Live session %s tick failed for strategy '%s': %s",
                session.id, session.strategy.name, exc,
            )
    return {"processed_sessions": processed}



@shared_task(name="live_trading.reconcile_all_active_accounts")
def reconcile_all_active_accounts():
    """
    Periodic task to ensure system state matches broker state for all active users.
    """
    from users.models import User
    # Only sync for users who have a RUNNING session or open positions
    active_user_ids = set(TradingSession.objects.filter(status="RUNNING").values_list("user_id", flat=True))
    
    synced_users = 0
    for user_id in active_user_ids:
        try:
            user = User.objects.get(id=user_id)
            LiveExecutionService.sync_account_state(user, force=True)
            synced_users += 1
        except Exception as exc:
            logger.exception(
                "Account reconciliation failed for user %s: %s", user_id, exc,
            )
            continue
            
    return {"synced_users": synced_users}


@shared_task(name="live_trading.refresh_broker_funds")
def refresh_broker_funds(credential_id):
    from brokers.models import BrokerCredential
    try:
        credential = BrokerCredential.objects.get(id=credential_id)
        LiveExecutionService._sync_funds_from_broker(credential, force=True, async_refresh=False)
    except Exception as exc:
        logger.warning("Failed refreshing broker funds for credential %s: %s", credential_id, exc)
