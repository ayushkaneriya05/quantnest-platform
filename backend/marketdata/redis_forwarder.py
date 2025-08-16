# backend/marketdata/redis_forwarder.py
import os
import json
import redis
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from trading.tasks import process_tick  # celery task

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
ch = get_channel_layer()

def run_forwarder():
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    # pattern subscribe to any delayed tick channel
    pubsub.psubscribe("pubsub:delayed:tick:*")
    for msg in pubsub.listen():
        if msg is None:
            continue
        # msg types include: subscribe, pmessage, message; we focus on pmessage and message
        if msg.get("type") not in ("pmessage", "message"):
            continue
        try:
            data_raw = msg.get("data")
            if isinstance(data_raw, bytes):
                data_raw = data_raw.decode("utf-8")
            data = json.loads(data_raw)
            symbol = data.get("symbol")
            # forward to channel layer group
            group = f"symbol_{symbol}"
            async_to_sync(ch.group_send)(group, {"type": "market.tick", "tick": data})
            # enqueue matching engine (process orders against this tick)
            # pass serialized tick to celery task
            process_tick.delay(symbol, json.dumps(data))
        except Exception:
            import logging
            logging.exception("Error in redis_forwarder processing message")

if __name__ == "__main__":
    run_forwarder()
