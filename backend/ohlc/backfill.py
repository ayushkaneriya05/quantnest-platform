# backend/ohlc/backfill.py
import os
import json
import time
import logging
from datetime import datetime, timezone
from celery import shared_task
from fyers_apiv3 import fyersModel
from .models import OHLC

logger = logging.getLogger(__name__)

FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
FYERS_SECRET = os.getenv("FYERS_SECRET")                    
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")
RATE_SLEEP = float(os.getenv("FYERS_BACKFILL_RATE_SEC", "0.6"))

def _get_fyers_client():
    cfg = {"client_id": FYERS_CLIENT_ID, "secret_key": FYERS_SECRET, "access_token": FYERS_ACCESS_TOKEN}
    return fyersModel.FyersModel(cfg)

@shared_task(bind=True)
def backfill_ohlc(self, symbols_json, resolution="1", start_ts=None, end_ts=None):
    """
    symbols_json: JSON array string of symbols e.g. '["RELIANCE","TCS"]'
    resolution: "1" for 1m, "5" for 5m, "15" etc (fyers resolution mapping)
    start_ts/end_ts: unix timestamp or ISO string. If None use last available.
    """
    symbols = json.loads(symbols_json) if isinstance(symbols_json, str) else symbols_json
    client = _get_fyers_client()
    inserted = 0

    for sym in symbols:
        try:
            fy_sym = sym if ":" in sym else f"NSE:{sym}-EQ"
            params = {
                "symbol": fy_sym,
                "resolution": resolution,
                "date_format": "1",
                # fyers history expects unix timestamps as strings (seconds)
            }
            if start_ts:
                try:
                    params["range_from"] = str(int(float(start_ts)))
                except Exception:
                    # try parse ISO
                    params["range_from"] = str(int(datetime.fromisoformat(start_ts).timestamp()))
            if end_ts:
                try:
                    params["range_to"] = str(int(float(end_ts)))
                except Exception:
                    params["range_to"] = str(int(datetime.fromisoformat(end_ts).timestamp()))

            logger.info("Backfill: requesting history for %s params=%s", fy_sym, params)
            res = client.history(params)
            candles = res.get("candles") or res.get("data") or []
            objs = []
            for row in candles:
                # Fyers often returns rows like [ts, o, h, l, c, v]
                if not isinstance(row, (list, tuple)) or len(row) < 6:
                    continue
                ts = int(row[0])
                if ts > 1e12:
                    # sometimes in ms
                    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                else:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                o = float(row[1]); h = float(row[2]); l = float(row[3]); c = float(row[4]); v = int(row[5])
                # save (update_or_create to avoid duplicates)
                OHLC.objects.update_or_create(symbol=sym, tf=f"{resolution}m", ts=dt, defaults={
                    "open": o, "high": h, "low": l, "close": c, "volume": v
                })
                inserted += 1
            time.sleep(RATE_SLEEP)
        except Exception:
            logger.exception("Backfill failed for %s", sym)
            time.sleep(RATE_SLEEP)
            continue

    return {"inserted": inserted}
