"""Dependency readiness for the HTTP endpoint and deployment command."""
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from common.redis import runtime_redis


def get_readiness_status(*, workers=False):
    """Probe dependencies without changing execution or starting workers."""
    status = {"database": False, "runtime": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status["database"] = cursor.fetchone()[0] == 1
    except Exception:
        pass
    try:
        client = runtime_redis()
        status["runtime"] = bool(client.ping())
        if workers:
            status["execution_workers"] = int(client.get("quantnest:execution:workers") or 0) == settings.EXECUTION_WORKERS
    except Exception:
        status["runtime"] = False
    if workers:
        status.setdefault("execution_workers", False)
    return status


@csrf_exempt
def health_check(request):
    checks = get_readiness_status()
    ready = all(checks.values())
    response = JsonResponse(
        {"status": "healthy" if ready else "unavailable", "mode": settings.QUANTNEST_DEPLOYMENT_MODE, "checks": checks},
        status=200 if ready else 503,
    )
    response["Cache-Control"] = "no-store"
    return response
