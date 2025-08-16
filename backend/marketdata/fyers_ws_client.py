# backend/marketdata/fyers_ws_client.py
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
import redis
import websockets

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

FYERS_WS = os.getenv("FYERS_WS_URL", "wss://ws.fyers.in")
FYERS_API_KEY = os.getenv("FYERS_API_KEY", "")

def normalize_fyers_tick(raw_msg: str):
    """
    Convert provider-specific message to:
    {"symbol":"RELIANCE","ts":"2025-08-15T10:03:21Z","last":2816.25,"bid":2816,"ask":2816.5,"volume":12345}
    This function needs adapting to actual Fyers message format.
    """
    try:
        data = json.loads(raw_msg)
        # example normalization (adjust to Fyers payload)
        symbol = data.get("symbol") or data.get("s") or data.get("instrument")
        last = float(data.get("ltp") or data.get("last") or data.get("price", 0))
        bid = float(data.get("bid", last))
        ask = float(data.get("ask", last))
        vol = int(data.get("volume") or data.get("v", 0))
        ts = datetime.now(timezone.utc).isoformat()
        return {"symbol": symbol, "ts": ts, "last": last, "bid": bid, "ask": ask, "volume": vol}
    except Exception:
        logger.exception("Failed to normalize fyers message")
        return None

async def run_fyers_ws_stub(subscribe_symbols=None):
    """
    Connect to Fyers WS and push raw live ticks into Redis sorted set.
    This implementation is a stub: adapt message parsing and subscription.
    """
    # If no API key, just simulate ticks (useful for local dev)
    if not FYERS_API_KEY:
        import random, time
        symbols = subscribe_symbols or ["RELIANCE", "TCS", "INFY"]
        while True:
            for s in symbols:
                tick = {
                    "symbol": s,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "last": round(1000 + random.random() * 1000, 2),
                    "bid": round(1000 + random.random() * 999, 2),
                    "ask": round(1000 + random.random() * 999, 2),
                    "volume": random.randint(100, 10000),
                }
                member = json.dumps(tick)
                score = int(datetime.now(timezone.utc).timestamp())
                r.zadd("live_ticks:zset", {member: score})
            await asyncio.sleep(1)
        return

    # Real connection (example - adapt to Fyers)
    async with websockets.connect(FYERS_WS, extra_headers={"Authorization": FYERS_API_KEY}) as ws:
        # subscribe message - actual format depends on Fyers
        if subscribe_symbols:
            sub_msg = {"action": "subscribe", "symbols": subscribe_symbols}
            await ws.send(json.dumps(sub_msg))
        async for raw in ws:
            tick = normalize_fyers_tick(raw)
            if not tick:
                continue
            member = json.dumps(tick)
            score = int(datetime.fromisoformat(tick["ts"]).timestamp())
            r.zadd("live_ticks:zset", {member: score})
            # admin only
            r.set(f"live:tick:{tick['symbol']}", member)
