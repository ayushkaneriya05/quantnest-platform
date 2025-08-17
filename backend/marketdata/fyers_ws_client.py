# backend/marketdata/fyers_ws_client.py
import os
import json
import logging
from datetime import datetime, timezone
import redis
from fyers_apiv3.FyersWebsocket import DataSocket  # precise class name per fyers_apiv3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")  # must be set
FYERS_SUBSCRIBE = os.getenv("FYERS_SUBSCRIBE", "")  # comma-separated list optional

def _normalize_fyers_tick(msg):
    """
    Convert Fyers data socket message into internal tick:
    {
      "symbol": "RELIANCE",
      "ts": "2025-08-17T12:34:56.123Z",
      "last": 1234.5,
      "bid": 1234.0,
      "ask": 1235.0,
      "volume": 1000
    }
    """
    try:
        # msg may be dict already from SDK callback
        if isinstance(msg, str):
            obj = json.loads(msg)
        else:
            obj = msg

        # Fyers data socket messages typically look like {'d': {...}}
        payload = obj.get("d") or obj.get("data") or obj or {}
        # example payload keys: 'symbol', 'ltp', 'best_bid', 'best_ask', 'volume', 'timestamp'
        sym_raw = payload.get("symbol") or payload.get("s")
        if not sym_raw:
            return None
        # keep symbol in simple form, e.g., "NSE:RELIANCE-EQ" -> "RELIANCE"
        sym = sym_raw.split(":")[-1].split("-")[0]

        ts_val = payload.get("timestamp") or payload.get("ts") or None
        if ts_val:
            try:
                ts_iso = datetime.fromtimestamp(float(ts_val)/1000, tz=timezone.utc).isoformat()
            except Exception:
                try:
                    ts_iso = datetime.fromtimestamp(float(ts_val), tz=timezone.utc).isoformat()
                except Exception:
                    ts_iso = datetime.now(timezone.utc).isoformat()
        else:
            ts_iso = datetime.now(timezone.utc).isoformat()

        last = payload.get("ltp") or payload.get("last_price") or payload.get("lp") or payload.get("last")
        bid = payload.get("best_bid") or payload.get("bid")
        ask = payload.get("best_ask") or payload.get("ask")
        vol = payload.get("volume") or payload.get("v") or 0

        if last is None:
            return None

        tick = {
            "symbol": sym,
            "ts": ts_iso,
            "last": float(last),
            "bid": float(bid) if bid is not None else None,
            "ask": float(ask) if ask is not None else None,
            "volume": int(vol) if vol is not None else 0
        }
        return tick
    except Exception:
        logger.exception("normalize error")
        return None

def _publish_tick(tick):
    member = json.dumps(tick, separators=(",", ":"))
    # use unix timestamp as score for zset
    try:
        score = int(datetime.fromisoformat(tick["ts"]).timestamp())
    except Exception:
        score = int(datetime.now(timezone.utc).timestamp())
    r.zadd("live_ticks:zset", {member: score})
    r.set(f"live:tick:{tick['symbol']}", member)
    r.publish(f"pubsub:live:tick:{tick['symbol']}", member)

def on_message(raw_msg):
    tick = _normalize_fyers_tick(raw_msg)
    if not tick:
        return
    _publish_tick(tick)

def on_error(e):
    logger.error("Fyers DataSocket error: %s", e)

def on_close():
    logger.info("Fyers DataSocket closed")

def on_open():
    logger.info("Fyers DataSocket connected")

def run(subscribe_symbols=None):
    """
    Start the Fyers data socket. subscribe_symbols is a list of simple symbol strings (e.g. ["RELIANCE","TCS"])
    """
    if not FYERS_ACCESS_TOKEN:
        logger.error("FYERS_ACCESS_TOKEN not set - cannot start data socket")
        return

    # build symbols for Fyers format if provided
    subs = []
    if subscribe_symbols:
        for s in subscribe_symbols:
            if ":" in s:
                subs.append(s)
            else:
                subs.append(f"NSE:{s}-EQ")

    # if FYERS_SUBSCRIBE env is set and no subscribe_symbols passed, use env
    if not subs and FYERS_SUBSCRIBE:
        subs = [p.strip() for p in FYERS_SUBSCRIBE.split(",") if p.strip()]

    logger.info("Starting Fyers DataSocket with subscribe=%s", subs or "ALL (if SDK supports)")

    ws = DataSocket()
    # configure callbacks per fyers_apiv3 SDK API
    ws.set_token(FYERS_ACCESS_TOKEN)
    ws.on_message = on_message
    ws.on_error = on_error
    ws.on_close = on_close
    ws.on_open = on_open

    # Connect (blocking call inside library)
    try:
        if subs:
            ws.connect(symbols=subs)
        else:
            ws.connect()
    except Exception:
        logger.exception("Fyers DataSocket.connect() failed")
