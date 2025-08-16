# backend/marketdata/candle_builder.py
import os, json
from datetime import datetime, timezone
import redis
from . import utils
from ohlc.tasks import flush_1m_from_redis_to_db

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def build_1m_from_raw_ticks(symbol, max_ticks=10000):
    """
    Read raw_delayed_ticks:<symbol> list (LRANGE), build minute candles for any completed minutes,
    push finalized candles to Postgres via Celery task flush_1m_from_redis_to_db, and trim the raw list.
    This function can be invoked periodically (every 10s) by a Celery task or the publisher.
    """
    raw_key = f"raw_delayed_ticks:{symbol}"
    # get all ticks currently (caller should limit frequency)
    ticks = r.lrange(raw_key, 0, -1)
    if not ticks:
        return {"candles": 0}
    # parse to dicts
    parsed = []
    for t in ticks:
        try:
            parsed.append(json.loads(t))
        except Exception:
            continue
    # sort by ts ascending
    parsed.sort(key=lambda x: x.get("ts"))
    # group into minute buckets (start at minute epoch)
    buckets = {}
    for tk in parsed:
        # parse ISO ts into minute epoch
        try:
            ts = datetime.fromisoformat(tk["ts"])
            ts = ts.replace(second=0, microsecond=0, tzinfo=timezone.utc)
            key = int(ts.timestamp())
        except Exception:
            continue
        b = buckets.setdefault(key, {"o": None, "h": None, "l": None, "c": None, "v": 0, "ts": datetime.fromtimestamp(key, tz=timezone.utc).isoformat()})
        price = float(tk.get("last", 0))
        if b["o"] is None:
            b["o"] = price
        b["h"] = price if b["h"] is None else max(b["h"], price)
        b["l"] = price if b["l"] is None else min(b["l"], price)
        b["c"] = price
        b["v"] += int(tk.get("volume", 0))
    # finalize buckets in chronological order
    sorted_keys = sorted(buckets.keys())
    # we will only finalize buckets that are older than current minute (safe)
    now_min = int(datetime.now(timezone.utc).replace(second=0, microsecond=0).timestamp())
    to_finalize = [k for k in sorted_keys if k < now_min]
    candles = []
    for k in to_finalize:
        b = buckets[k]
        candles.append({"ts": b["ts"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]})
    if candles:
        # flush to DB using Celery task
        # group by symbol and call flush
        flush_1m_from_redis_to_db.delay(symbol, candles)
        # trim raw list: remove ticks that belong to finalized minutes
        # efficient trimming: rebuild raw list excluding finalized minute ticks
        remaining = []
        for tk in parsed:
            try:
                ts = datetime.fromisoformat(tk["ts"])
                ts_min = int(ts.replace(second=0, microsecond=0, tzinfo=timezone.utc).timestamp())
                if ts_min in to_finalize:
                    continue
                remaining.append(json.dumps(tk))
            except Exception:
                continue
        # overwrite raw list
        pipe = r.pipeline()
        pipe.delete(raw_key)
        if remaining:
            pipe.rpush(raw_key, *remaining)
        pipe.execute()
    return {"candles": len(candles)}
