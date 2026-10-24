"""Shared process-local connection pool for runtime Redis."""
import os
from functools import lru_cache

import redis
from django.conf import settings


@lru_cache(maxsize=8)
def _client(pid, url):
    return redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=5, health_check_interval=15)


def runtime_redis():
    """Reuse a connection pool within a process, including after a worker fork."""
    return _client(os.getpid(), settings.RUNTIME_REDIS_URL)
