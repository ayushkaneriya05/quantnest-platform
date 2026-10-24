"""Adapter selection and one shared request budget for market-data HTTP calls."""
import time
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils.module_loading import import_string
from common.redis import runtime_redis
from .contracts import ProviderError

# Reserve spacing and daily counters together; refused requests use no budget.
REQUEST_BUDGET = """
if tonumber(redis.call('GET', KEYS[2]) or '0') >= tonumber(ARGV[2]) then return -1 end
local remaining = redis.call('PTTL', KEYS[1])
if remaining > 0 then return remaining end
redis.call('SET', KEYS[1], '1', 'PX', ARGV[1])
redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], 172800)
return 0
"""


@lru_cache(maxsize=1)
def provider():
    from .fyers import FyersProvider
    implementation = {"fyers": FyersProvider}.get(settings.MARKET_DATA_PROVIDER)
    return (implementation or import_string(settings.MARKET_DATA_PROVIDER))()


def live_client():
    return provider().live_client()


def acquire_data_request(adapter, *, wait_seconds=5):
    """Apply the same account budget to history and quotes in every process."""
    zone = ZoneInfo(adapter.quota_timezone)
    prefix = f"quantnest:data-budget:{adapter.name}:{adapter.account_key}"
    deadline = time.monotonic() + wait_seconds
    while True:
        day = datetime.now(zone).date().isoformat()
        delay = int(runtime_redis().eval(
            REQUEST_BUDGET, 2, f"{prefix}:spacing", f"{prefix}:{day}",
            adapter.request_interval_ms, adapter.daily_request_limit,
        ))
        if delay == 0:
            return
        if delay < 0:
            raise ProviderError("The market-data account's daily request budget is exhausted.")
        if time.monotonic() + delay / 1000 > deadline:
            raise ProviderError("Market-data requests are busy; retry shortly.")
        time.sleep(delay / 1000)
