"""Prune published records; pending financial publications are never discarded."""
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task(name="common.prune_runtime_records")
def prune_runtime_records():
    from common.models import RuntimeOutbox
    from core.redis import runtime_redis
    cutoff = timezone.now() - timedelta(days=7)
    deleted = 0
    # One bounded batch per beat invocation avoids long table locks and vacuum spikes.
    ids = list(RuntimeOutbox.objects.filter(published_at__lt=cutoff).order_by("pk").values_list("pk", flat=True)[:10000])
    if ids:
        deleted, _ = RuntimeOutbox.objects.filter(pk__in=ids).delete()
    from common.models import RuntimeAssignment
    from live_trading.models import TradingSession
    from paper_trading.models import PaperTradingSession
    from django.db.models import Exists, OuterRef, BigIntegerField
    from django.db.models.functions import Cast
    for scope, model in (("paper", PaperTradingSession), ("live", TradingSession)):
        existing = model.objects.filter(pk=Cast(OuterRef("session_id"), BigIntegerField())).exclude(status="STOPPED")
        stale = list(RuntimeAssignment.objects.filter(scope=scope).annotate(
            session_exists=Exists(existing)).filter(session_exists=False).values_list("pk", flat=True)[:1000])
        if stale:
            RuntimeAssignment.objects.filter(pk__in=stale).delete()
    client = runtime_redis()
    # Lifecycle streams are recoverable from their complete atomic state projection.
    timestamp = int((timezone.now() - timedelta(days=2)).timestamp() * 1000)
    for key in client.scan_iter(match="quantnest:lifecycle:*", count=100):
        client.xtrim(key, minid=f"{timestamp}-0", approximate=True)
    client.xtrim("execution_control", minid=f"{timestamp}-0", approximate=True)
    # Terminal books require every owner to report consumption before trimming.
    total = settings.ORDER_WORKERS * settings.EXECUTION_NODE_COUNT
    cursors = client.mget([f"quantnest:terminal:cursor:{index}" for index in range(total)])
    if all(cursors):
        minimum = min(cursors, key=lambda value: tuple(map(int, value.split("-"))))
        client.xtrim("quantnest:terminal:commands", minid=minimum, approximate=True)
    return {"published_outbox_removed": deleted}
