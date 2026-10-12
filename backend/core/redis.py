"""Fork-safe connection pools for execution, separate from analytical caches."""
import os
from functools import lru_cache
from django.conf import settings
import redis


@lru_cache(maxsize=8)
def _client(pid, url, decode):
    return redis.Redis.from_url(url, decode_responses=decode, socket_connect_timeout=3,
                                socket_timeout=5, health_check_interval=15)


def runtime_redis(decode=True):
    return _client(os.getpid(), settings.RUNTIME_REDIS_URL, decode)
