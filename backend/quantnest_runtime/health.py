"""Readiness checks expose component status without account or broker details."""
from django.db import connection
from core.redis import runtime_redis


def readiness():
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
    return status
