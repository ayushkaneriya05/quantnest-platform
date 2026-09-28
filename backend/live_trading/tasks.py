import logging

from celery import shared_task

from .models import TradingSession

logger = logging.getLogger(__name__)


@shared_task(name="live_trading.reconcile_all_active_accounts")
def reconcile_all_active_accounts(credential_id=None):
    """
    Ensure system state matches broker state for active live sessions.

    When ``credential_id`` is provided, reconcile only sessions using that
    broker credential. The periodic Celery Beat invocation omits it and keeps
    reconciling all active accounts.
    """
    from live_trading.reconciliation_service import BrokerReconciliationService
    
    # Include paused/stopping sessions and sessions with unresolved orders or
    # open positions so WebSocket failure never disables REST reconciliation.
    from django.db.models import Q
    from common.enums import OrderStatus
    active_statuses = [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN"]
    active_sessions = TradingSession.objects.filter(Q(status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"])
        | Q(orders__status__in=active_statuses)
        | Q(allocation__positions__quantity__gt=0)
    ).distinct()

    if credential_id is not None:
        active_sessions = active_sessions.filter(broker_credential_id=credential_id)
    active_sessions = active_sessions.select_related("broker_credential")

    # Refresh broker funds and allocation health once per credential, not once
    # per session. Keep this REST work in the background reconciliation task.
    from live_trading.services import LiveExecutionService

    active_sessions = list(active_sessions)
    credentials = {session.broker_credential_id: session.broker_credential for session in active_sessions if session.broker_credential_id and session.broker_credential}

    for session in active_sessions:
        try:
            if session.broker_credential:
                reconciliation_service = BrokerReconciliationService(session)
                reconciliation_service.reconcile_orders()
                # reconciliation_service.reconcile_positions()
        except Exception as exc:
            logger.exception("Account reconciliation failed for user %s: %s", session.user_id, exc)
            continue

    # Refresh after order/position reconciliation so allocation capital is
    # computed from the latest durable state.
    for credential in credentials.values():
        try:
            LiveExecutionService.sync_funds(credential)
            LiveExecutionService._refresh_broker_allocation_health(credential)
        except Exception:
            logger.exception("Funds/allocation refresh failed for credential %s", credential.id)

    return
