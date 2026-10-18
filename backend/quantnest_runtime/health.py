"""Readiness checks expose component status without account or broker details."""
from django.db import connection
from core.redis import runtime_redis


def get_readiness_status(*, workers=False):
    status = {"database": False, "runtime": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status["database"] = cursor.fetchone()[0] == 1
    except Exception:
        pass
    try:
        status["runtime"] = bool(runtime_redis().ping())
    except Exception:
        pass
    if workers:
        from django.conf import settings
        import json
        import time
        try:
            count = settings.EXECUTION_WORKERS * settings.EXECUTION_NODE_COUNT
            values = runtime_redis().mget([f"quantnest:health:execution:{index}" for index in range(count)])
            status["execution_workers"] = bool(count and all(value and time.time() - json.loads(value)["at"] < 15 for value in values))
        except Exception:
            status["execution_workers"] = False
    return status
