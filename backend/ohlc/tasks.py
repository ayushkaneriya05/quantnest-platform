# backend/ohlc/tasks.py
import os, json
import redis
from celery import shared_task
from datetime import datetime, timezone, timedelta
from .models import OHLC
from django.db import transaction

REDIS_URL = os.getenv("REDIS_URL","redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

@shared_task
def flush_1m_from_redis_to_db(symbol, candles_list):
    """
    candles_list: list of dicts {ts, o,h,l,c,v}
    """
    objs = []
    for c in candles_list:
        objs.append(OHLC(
            symbol=symbol, tf="1m",
            ts=c["ts"], open=c["o"], high=c["h"], low=c["l"], close=c["c"], volume=c["v"]
        ))
    if objs:
        with transaction.atomic():
            OHLC.objects.bulk_create(objs, ignore_conflicts=True)
    return {"inserted": len(objs)}
