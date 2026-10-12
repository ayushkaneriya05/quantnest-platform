"""Cold finalization after all owned financial obligations have settled."""
from django.db import transaction
from django.utils import timezone


@transaction.atomic
def finalize_stop(scope, session):
    if session.status != "STOPPING":
        return False
    from brokers.models import BrokerCredential
    from live_trading.models import LiveOrder, LivePosition
    from paper_trading.models import PaperAccount, PaperOrder, PaperPosition
    from common.models import RuntimeAssignment
    from core.redis import runtime_redis
    from strategy_engine.order_queue import pending_key
    if scope == "live":
        BrokerCredential.objects.select_for_update().get(pk=session.broker_credential_id)
        positions = LivePosition.objects.filter(allocation_id=session.allocation_id, quantity__gt=0)
        orders = LiveOrder.objects.filter(session_id=session.pk)
    else:
        PaperAccount.objects.select_for_update().get(pk=session.account_id)
        positions = PaperPosition.objects.filter(account_id=session.account_id, strategy_id=session.strategy_id, quantity__gt=0)
        orders = PaperOrder.objects.filter(account_id=session.account_id, strategy_id=session.strategy_id)
    locked = session.__class__.objects.select_for_update().get(pk=session.pk)
    if locked.status != "STOPPING" or positions.exists() or orders.filter(
            status__in=["PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"]).exists():
        return False
    instruments = RuntimeAssignment.objects.filter(scope=scope, session_id=str(session.pk)).values_list("instrument_id", flat=True)
    keys = [pending_key(scope, session.pk, identity) for identity in instruments]
    if keys and any(runtime_redis().mget(keys)):
        return False
    locked.status, locked.error_message, locked.ended_at = "STOPPED", "", timezone.now()
    locked.save(update_fields=["status", "error_message", "ended_at", "updated_at"])
    from core.outbox import enqueue
    enqueue("control", f"{scope}:{session.pk}", {"scope": scope, "session_id": str(session.pk), "action": "SESSION_STOP"})
    return True
