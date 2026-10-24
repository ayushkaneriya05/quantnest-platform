import logging

from celery import shared_task

from brokers.models import BrokerCredential
from execution.order_reports import ACTIVE
from .models import TradingSession

logger = logging.getLogger(__name__)


@shared_task(name="live_trading.reconcile_all_active_accounts")
def reconcile_all_active_accounts(credential_id=None):
    """
    Reconcile owned orders and refresh broker funds for active live sessions.

    When ``credential_id`` is provided, reconcile only sessions using that
    broker credential. The periodic Celery Beat invocation omits it and keeps
    reconciling all active accounts.
    """
    from live_trading.order_processor import reconcile_orders
    
    # Include paused/stopping sessions and sessions with unresolved orders or
    # open positions so WebSocket failure never disables REST reconciliation.
    from django.db.models import Q
    active_sessions = TradingSession.objects.filter(Q(status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"])
        | Q(orders__status__in=ACTIVE)
        | Q(allocation__positions__quantity__gt=0)
    ).distinct()

    if credential_id is not None:
        active_sessions = active_sessions.filter(broker_credential_id=credential_id)
    # Refresh broker funds and allocation health once per credential, not once
    # per session. Keep this REST work in the background reconciliation task.
    from live_trading.services import LiveExecutionService

    credentials = BrokerCredential.objects.filter(pk__in=active_sessions.values("broker_credential_id"))
    for credential in credentials:
        try:
            reconcile_orders(credential)
        except Exception:
            logger.exception("Account reconciliation failed credential=%s", credential.pk)

        # Refresh after reconciliation using this account's latest durable fills.
        try:
            LiveExecutionService.sync_funds(credential)
            LiveExecutionService._refresh_broker_allocation_health(credential)
        except Exception:
            logger.exception("Funds/allocation refresh failed for credential %s", credential.id)
