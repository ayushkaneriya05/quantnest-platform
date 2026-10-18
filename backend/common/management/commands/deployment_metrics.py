"""Bounded, content-free operations metrics outside the execution path."""
import json
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from common.models import RuntimeOutbox
from core.redis import runtime_redis
from quantnest_runtime.health import get_readiness_status


class Command(BaseCommand):
    def handle(self, *args, **options):
        checks = get_readiness_status(workers=True)
        oldest = RuntimeOutbox.objects.filter(published_at__isnull=True).order_by("id").values_list("created_at", flat=True).first()
        metrics = {
            "database_ok": int(checks["database"]),
            "execution_workers_ok": int(checks.get("execution_workers", False)),
            "outbox_oldest_seconds": max(0, (timezone.now() - oldest).total_seconds()) if oldest else 0,
            "order_pending_idle_seconds": 0,
        }
        client = runtime_redis()
        for scope in settings.EXECUTION_ENABLED_SCOPES:
            for partition in range(settings.ORDER_PARTITIONS):
                key = f"quantnest:orders:{scope}:{partition}"
                try:
                    pending = client.xpending_range(key, "execution", "-", "+", 1)
                    if pending:
                        metrics["order_pending_idle_seconds"] = max(metrics["order_pending_idle_seconds"], pending[0]["time_since_delivered"] / 1000)
                    groups = client.xinfo_groups(key)
                    for group in groups:
                        if group.get("name") in {"execution", b"execution"} and group.get("lag", 0):
                            rows = client.xrange(key, min="(" + str(group["last-delivered-id"].decode() if isinstance(group["last-delivered-id"], bytes) else group["last-delivered-id"]), count=1)
                            if rows:
                                identity = rows[0][0].decode() if isinstance(rows[0][0], bytes) else rows[0][0]
                                metrics["order_pending_idle_seconds"] = max(metrics["order_pending_idle_seconds"], max(0, time.time() - int(identity.split('-')[0]) / 1000))
                except Exception as failure:
                    # Missing never-used streams/groups are normal; other failures are unhealthy.
                    if 'no such key' not in str(failure).lower() and 'nogroup' not in str(failure).lower():
                        metrics["order_pending_idle_seconds"] = 3600
        self.stdout.write(json.dumps(metrics))
