"""Persist publications in the transaction that changes financial state."""
import json
import logging
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from common.models import RuntimeOutbox

logger = logging.getLogger(__name__)


@transaction.atomic
def enqueue(topic, aggregate_key, payload):
    if topic == "control":
        from core.assignments import synchronize
        synchronize(payload["scope"], payload["session_id"])
    payload = json.loads(json.dumps(payload, cls=DjangoJSONEncoder))
    return RuntimeOutbox.objects.create(topic=topic, aggregate_key=aggregate_key, payload=payload)


def cache_event(method, *args, **kwargs):
    key = ":".join(str(value) for value in args[:2])
    return enqueue("cache", key, {"method": method, "args": args, "kwargs": kwargs})


def deliver(event):
    if event.topic == "runtime":
        from core.runtime_projection import update
        value = event.payload
        update(value["scope"], value["session_id"], value["instrument_id"],
               value["updates"], event.pk)
    elif event.topic == "control":
        from core.redis import runtime_redis
        runtime_redis().xadd("execution_control", {"payload": json.dumps(event.payload),
                                                   "revision": event.pk})
    elif event.topic == "terminal":
        from core.redis import runtime_redis
        runtime_redis().xadd("quantnest:terminal:commands", {"payload": json.dumps(event.payload),
                                                            "revision": event.pk})
    elif event.topic == "cache":
        from core.shared_state_store import shared_state_store
        value = event.payload
        getattr(shared_state_store, value["method"])(*value["args"], **value["kwargs"])
    elif event.topic == "risk":
        from decimal import Decimal
        from django.utils.dateparse import parse_datetime
        from live_trading.models import TradingSession
        from paper_trading.models import PaperTradingSession
        from risk_management.auto_disable import AutoDisableGate
        value = event.payload
        model = TradingSession if value["scope"] == "live" else PaperTradingSession
        session = model.objects.select_related("allocation__deployed_version").filter(pk=value["session_id"]).first()
        if session and session.allocation.deployed_version_id == value["version_id"]:
            AutoDisableGate.record_close(session, value["trade_id"], Decimal(value["pnl"]),
                parse_datetime(value["timestamp"]), Decimal(value["capital"]), value["config"])
    else:
        raise ValueError(f"Unsupported outbox topic {event.topic}")


def relay_batch(limit=100):
    """Each aggregate is ordered by commit record; failures block its successors."""
    delivered = 0
    blocked = set()
    predecessors = RuntimeOutbox.objects.filter(
        published_at__isnull=True, topic=OuterRef("topic"),
        aggregate_key=OuterRef("aggregate_key"), id__lt=OuterRef("id"))
    # Bound the batch by independent aggregate heads. A failed aggregate must
    # not fill the whole batch with successors that cannot yet be delivered.
    ids = list(RuntimeOutbox.objects.filter(published_at__isnull=True).filter(~Exists(predecessors)).order_by("id")
               .values_list("id", flat=True)[:limit])
    for event_id in ids:
        with transaction.atomic():
            event = RuntimeOutbox.objects.select_for_update(skip_locked=True).filter(
                pk=event_id, published_at__isnull=True).first()
            if event is None or (event.topic, event.aggregate_key) in blocked:
                continue
            if RuntimeOutbox.objects.filter(topic=event.topic, aggregate_key=event.aggregate_key,
                                            published_at__isnull=True, id__lt=event.pk).exists():
                continue
            try:
                # A failed database projection must roll back its own writes
                # without poisoning the transaction that records the retry.
                with transaction.atomic():
                    deliver(event)
                event.published_at = timezone.now()
                event.error = ""
                delivered += 1
            except Exception as exc:
                event.error = type(exc).__name__
                blocked.add((event.topic, event.aggregate_key))
                logger.exception("Outbox publication failed event=%s topic=%s", event.pk, event.topic)
            event.attempts += 1
            event.save(update_fields=["published_at", "attempts", "error", "updated_at"])
    return delivered
