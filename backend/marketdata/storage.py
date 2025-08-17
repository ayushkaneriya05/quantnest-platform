# backend/marketdata/storage.py
import os, json
from datetime import datetime, timezone
import redis
from django.db import transaction
from ohlc.models import OHLC

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def persist_raw_tick(symbol: str, tick: dict):
    """
    Persist raw tick to a Postgres table or append to file.
    For simplicity we append to a Redis list and have periodic flush to DB (via Celery).
    """
    r.rpush(f"raw_ticks:{symbol}", json.dumps(tick))

def get_bootstrap_ohlc(symbol: str, tf: str = "1m", limit: int = 200):
    """
    Retrieve last N OHLC from Postgres (ohlc table) for bootstrap.
    """
    qs = OHLC.objects.filter(symbol=symbol, tf=tf).order_by("-ts")[:limit]
    # return ordered oldest->newest
    rev = list(reversed(qs))
    out = []
    for c in rev:
        out.append({
            "ts": c.ts.isoformat(),
            "o": float(c.open),
            "h": float(c.high),
            "l": float(c.low),
            "c": float(c.close),
            "v": int(c.volume),
        })
    return out