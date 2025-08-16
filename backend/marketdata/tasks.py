# backend/marketdata/tasks.py
import os
import json
from datetime import datetime, timezone
import redis
from celery import shared_task
from django.conf import settings

from trading.services.order_execution import process_slm_triggers
from ohlc.tasks import flush_1m_from_redis_to_db
from .candle_builder import build_1m_from_raw_ticks

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

DELAY_S = int(os.getenv("DATA_PUBLISH_DELAY_SECONDS", "900"))
BATCH_LIMIT = int(os.getenv("DELAY_BATCH_LIMIT", "500"))

@shared_task
def publish_delayed_ticks():
    """
    Move ticks older than threshold from live_ticks:zset to delayed and publish.
    """
    import logging
    now_ts = int(datetime.now(timezone.utc).timestamp())
    threshold = now_ts - DELAY_S
    members = r.zrangebyscore("live_ticks:zset", min=-1_000_000_000, max=threshold, start=0, num=BATCH_LIMIT)
    if not members:
        return {"published": 0}
    pipe = r.pipeline()
    published = 0
    for m in members:
        try:
            tick = json.loads(m)
            sym = tick.get("symbol")
            pipe.set(f"delayed:tick:{sym}", json.dumps(tick))
            pipe.publish(f"pubsub:delayed:tick:{sym}", json.dumps(tick))
            pipe.rpush(f"raw_delayed_ticks:{sym}", json.dumps(tick))
            pipe.zrem("live_ticks:zset", m)
            published += 1
        except Exception:
            logging.exception("publish tick error")
    pipe.execute()
    return {"published": published}


@shared_task
def build_and_flush_1m_for_active_symbols(batch_limit=200):
    """
    Called by Celery beat: enumerates active symbols and finalizes 1m candles.
    """
    try:
        syms = list(r.smembers("active_symbols") or [])
    except Exception:
        syms = []
    if not syms:
        # optional fallback: read from DB list (not implemented)
        return {"processed": 0}
    processed = 0
    candles_total = 0
    for s in syms[:batch_limit]:
        res = build_1m_from_raw_ticks(s)
        processed += 1
        candles_total += res.get("candles", 0)
    return {"processed": processed, "candles": candles_total}


@shared_task
def auto_close_intraday_positions():
    """
    Run at EOD (market close) to auto-square intraday positions if necessary.
    This is simplified: closes all MIS positions at the last delayed LTP.
    """
    try:
        keys = r.keys("active_users:*")  # optional: store users to iterate
        # simplified approach: find all open intraday positions (MIS product not tracked here)
        from trading.models import PaperPosition
        positions = PaperPosition.objects.filter(qty__ne=0)  # Django-style pseudocode; write appropriate filter
        # In practice, filter by product_type or an intraday flag in positions/orders
        for p in positions:
            ltp_raw = r.get(f"delayed:tick:{p.symbol}")
            if not ltp_raw:
                continue
            ltp = json.loads(ltp_raw).get("last")
            # generate an order to close at market
            # create synthetic order and fill
            from trading.models import PaperOrder
            from trading.services.order_execution import execute_market_fill
            # create order model for closing
            if p.qty > 0:
                # close long: SELL
                o = PaperOrder.objects.create(user=p.user, symbol=p.symbol, side="SELL", qty=abs(p.qty), order_type=PaperOrder.ORDER_MARKET, status=PaperOrder.STATUS_PENDING)
                execute_market_fill(o, o.qty, Decimal(str(ltp)))
            elif p.qty < 0:
                o = PaperOrder.objects.create(user=p.user, symbol=p.symbol, side="BUY", qty=abs(p.qty), order_type=PaperOrder.ORDER_MARKET, status=PaperOrder.STATUS_PENDING)
                execute_market_fill(o, o.qty, Decimal(str(ltp)))
    except Exception:
        import logging
        logging.exception("auto close error")
    return {"ok": True}
