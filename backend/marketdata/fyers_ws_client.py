# backend/marketdata/fyers_ws_client.py
"""
Fyers API v3 WebSocket runner (data-websocket).
Supports 'lite' (LTP only) and 'symbolUpdate' (full tick) modes.
On every incoming tick:
 - Persist to Redis list raw_ticks:<symbol>
 - Add JSON tick to zset live_ticks:zset with score=epoch_seconds
 - Publish immediate pubsub:live:tick:<symbol> (optional)
This implementation is defensive about the exact fyers_apiv3 import shape:
 - Tries fyers_apiv3.FyersWebsocket.data_ws if available
 - Falls back to fyers_apiv3.fyersModel.FyersDataSocket-like wrappers
"""

import os
import json
import time
import traceback
from datetime import datetime, timezone
from typing import List, Optional
import redis

# Corrected fyers v3 entrypoints
try:
    from fyers_apiv3.FyersWebsocket import data_ws
except ImportError:
    data_ws = None

try:
    from fyers_apiv3 import fyersModel
except ImportError:
    fyersModel = None

# repo helpers
try:
    from marketdata.utils import get_active_fyers_access_token
except Exception:
    def get_active_fyers_access_token():
        return os.getenv("FYERS_ACCESS_TOKEN", "")

try:
    from marketdata.storage import persist_raw_tick
except Exception:
    persist_raw_tick = None

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def _symbol_from_tick(tick_obj: dict) -> Optional[str]:
    return tick_obj.get("symbol")

def _ts_from_tick(tick_obj: dict) -> int:
    for k in ("last_traded_time", "exch_feed_time", "timestamp", "ts"):
        if k in tick_obj:
            try:
                val = tick_obj[k]
                if isinstance(val, (int, float)):
                    return int(val)
                else:
                    dt = datetime.fromisoformat(val)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return int(dt.timestamp())
            except Exception:
                continue
    return int(datetime.now(timezone.utc).timestamp())

class FyersWSRunner:
    def __init__(self, client_id: str, mode: str = "symbolUpdate"):
        self.client_id = client_id or os.getenv("FYERS_CLIENT_ID", "")
        self.mode = mode or "symbolUpdate"
        self._running = False
        self._ws_instance = None

    def _handle_payload(self, raw):
        try:
            payload = raw if isinstance(raw, dict) else json.loads(raw)
            # FYERS often wraps data in 'd' or 'data'
            records = []
            if isinstance(payload, dict):
                if "d" in payload and isinstance(payload["d"], list):
                    records = payload["d"]
                elif "data" in payload and isinstance(payload["data"], list):
                    records = payload["data"]
                else:
                    records = [payload]
            elif isinstance(payload, list):
                records = payload

            for rec in records:
                if not isinstance(rec, dict):
                    continue
                sym = _symbol_from_tick(rec)
                if not sym:
                    continue
                ts_epoch = _ts_from_tick(rec)
                tick = {"symbol": sym, "ts": ts_epoch, "payload": rec}

                # persist raw ticks list (bounded)
                try:
                    if persist_raw_tick:
                        persist_raw_tick(sym, tick)
                    else:
                        key = f"raw_ticks:{sym}"
                        r.rpush(key, json.dumps(tick, default=str))
                        r.ltrim(key, -2000, -1)
                except Exception:
                    print("persist_raw_tick failed:", traceback.format_exc())

                # zadd live_ticks:zset
                try:
                    serialized = json.dumps(tick, default=str)
                    r.zadd("live_ticks:zset", {serialized: int(ts_epoch)})
                except Exception:
                    print("zadd failed", traceback.format_exc())

                # immediate pubsub for realtime listeners (optional)
                try:
                    r.publish(f"pubsub:live:tick:{sym}", json.dumps(tick, default=str))
                except Exception:
                    pass

        except Exception:
            print("error in _handle_payload:", traceback.format_exc())

    def _attach_callbacks_to_fyers_ws(self, ws_obj):
        """
        Attach callbacks depending on library interface.
        For data_ws, docs often show `ws_obj.connect(on_message=...)` or
        `data_ws.Websocket(...)` that accepts callbacks. We'll attempt to attach common attrs.
        """
        if ws_obj is None:
            return
        # many wrappers call .on_message or .on_data
        if hasattr(ws_obj, "on_data"):
            try:
                setattr(ws_obj, "on_data", self._handle_payload)
            except Exception:
                pass
        if hasattr(ws_obj, "on_message"):
            try:
                setattr(ws_obj, "on_message", self._handle_payload)
            except Exception:
                pass

    def _create_and_start(self, subscribe_symbols: List[str]):
        """
        Create a websocket object using available fyers v3 entrypoints and start it.
        This method is intentionally tolerant to different packaging shapes.
        """
        token = get_active_fyers_access_token()
        # Try the recommended data_ws (FyersWebsocket) if available
        if data_ws is not None:
            try:
                ws = data_ws.Websocket(token=token, on_message=self._handle_payload, mode=self.mode)
                ws.connect()
                if subscribe_symbols:
                    ws.subscribe(subscribe_symbols, mode=self.mode)
                self._ws_instance = ws
                return ws
            except Exception:
                print("data_ws path failed, falling back:", traceback.format_exc())

        # fallback to fyersModel / other wrappers
        if fyersModel is not None:
            try:
                ws = None
                if hasattr(fyersModel, "FyersDataSocket"):
                    ws = fyersModel.FyersDataSocket(access_token=f"{self.client_id}:{token}")
                elif hasattr(fyersModel, "FyersWebsocket"):
                    ws = fyersModel.FyersWebsocket(access_token=f"{self.client_id}:{token}")
                if ws is None:
                    raise RuntimeError("no usable ws constructor in fyersModel")
                self._attach_callbacks_to_fyers_ws(ws)
                if hasattr(ws, "subscribe") and subscribe_symbols:
                    try:
                        ws.subscribe(symbols=subscribe_symbols, data_type=self.mode)
                    except Exception:
                        try:
                            ws.subscribe(subscribe_symbols)
                        except Exception:
                            pass
                if hasattr(ws, "start"):
                    ws.start()
                elif hasattr(ws, "run_forever"):
                    ws.run_forever()
                else:
                    while self._running:
                        time.sleep(1)
                self._ws_instance = ws
                return ws
            except Exception:
                print("fyersModel fallback failed:", traceback.format_exc())

        raise RuntimeError("No usable fyers websocket implementation found in environment.")

    def start_blocking(self, subscribe_symbols: Optional[List[str]] = None):
        self._running = True
        backoff = 1
        max_backoff = 60
        symbols = subscribe_symbols or []
        while self._running:
            try:
                self._create_and_start(symbols)
                backoff = 1
            except KeyboardInterrupt:
                self._running = False
                break
            except Exception:
                print("ws connect error, backoff:", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    def stop(self):
        self._running = False
        if self._ws_instance:
            try:
                if hasattr(self._ws_instance, "close"):
                    self._ws_instance.close()
                elif hasattr(self._ws_instance, "close_connection"):
                    self._ws_instance.close_connection()
            except Exception:
                pass

_global_runner = None

def run_fyers_ws(subscribe_symbols: Optional[List[str]] = None, client_id: Optional[str] = None, mode: str = "symbolUpdate"):
    global _global_runner
    cid = client_id or os.getenv("FYERS_CLIENT_ID") or ""
    _global_runner = FyersWSRunner(client_id=cid, mode=mode)
    _global_runner.start_blocking(subscribe_symbols or [])

def run_forever_from_env():
    syms = os.getenv("FYERS_SUBSCRIBE_SYMBOLS", "")
    subs = [s.strip().upper() for s in syms.split(",") if s.strip()] if syms else []
    mode = os.getenv("FYERS_WS_MODE", "symbolUpdate")
    run_fyers_ws(subs, mode=mode)

if __name__ == "__main__":
    run_forever_from_env()