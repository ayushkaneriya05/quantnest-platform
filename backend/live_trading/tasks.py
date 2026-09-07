import logging

from celery import shared_task

from .models import TradingSession
from .services import LiveExecutionService

logger = logging.getLogger(__name__)


@shared_task(name="live_trading.reconcile_all_active_accounts")
def reconcile_all_active_accounts():
    """
    Periodic task to ensure system state matches broker state for all active users.
    Updated to use new BrokerReconciliationService instead of old sync methods.
    """
    from users.models import User
    from live_trading.reconciliation_service import BrokerReconciliationService
    
    # Only sync for users who have a RUNNING session or open positions
    active_sessions = TradingSession.objects.filter(status="RUNNING")
    
    synced_users = 0
    for session in active_sessions:
        try:
            user = User.objects.get(id=session.user_id)
            if session.broker_credential:
                # Use new BrokerReconciliationService
                reconciliation_service = BrokerReconciliationService(session.broker_credential)
                reconciliation_service.reconcile_orders()
                reconciliation_service.reconcile_positions()
                synced_users += 1
        except Exception as exc:
            logger.exception(
                "Account reconciliation failed for user %s: %s", session.user_id, exc,
            )
            continue
            
    return {"synced_users": synced_users}
