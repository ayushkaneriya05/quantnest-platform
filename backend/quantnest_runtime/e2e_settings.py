"""Disposable PostgreSQL + private Redis settings for transport benchmarks."""
import os
from quantnest_runtime.test_postgres_settings import *  # noqa: F403

RUNTIME_REDIS_URL = os.environ["QUANTNEST_E2E_REDIS_URL"]
REDIS_URL = RUNTIME_REDIS_URL
CELERY_BROKER_URL = RUNTIME_REDIS_URL
CELERY_RESULT_BACKEND = RUNTIME_REDIS_URL
CACHES = {name: {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": RUNTIME_REDIS_URL,
                "KEY_PREFIX": f"e2e-{name}"}
          for name in ("default", "marketdata", "research")}
EXECUTION_WORKERS = 1
CALCULATION_WORKERS = 1
ORDER_WORKERS = 1
ORDER_CONCURRENCY = 2
EXECUTION_NODE_COUNT = 1
EXECUTION_NODE_INDEX = 0
EXECUTION_NOTIFY_PORT = int(os.environ["QUANTNEST_E2E_NOTIFY_PORT"])
EXECUTION_MAX_ACTORS = 50
EXECUTION_MAX_USER_ACTORS = 16
EXECUTION_ENABLED_SCOPES = ("paper", "live")
CALCULATION_CACHE_MB = 32
