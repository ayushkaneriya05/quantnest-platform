# backend/ohlc/backfill.py
"""
Historical OHLC fetcher using FYERS API v3 `history` endpoint.
Provides functions to fetch and optionally save OHLC candles to DB.
"""

import json
from datetime import datetime, date
from typing import List, Optional
import time

from marketdata.utils import build_fyers_rest_client, get_active_fyers_access_token

# Django ORM models - adapt import if your models are placed differently
try:
    from ohlc.models import Candle  # assume Candle model exists with fields: symbol, timestamp, open, high, low, close, volume
except Exception:
    Candle = None

# resolution mapping: user-friendly -> API resolution strings (minutes/days)
DEFAULT_TIMEOUT = 30  # seconds

def _api_resolution_from_minutes(minutes: int) -> str:
    # FYERS supports resolution like "1" (1 minute), "5", "15", "60", "D" etc.
    if minutes >= 1440:
        return "D"
    return str(minutes)

def fetch_historical(symbol: str, from_date: date, to_date: date, resolution_minutes: int = 1, save_to_db: bool = True, client_id: Optional[str] = None):
    """
    Fetch historical OHLC from FYERS and (optionally) store in Candle model.
    from_date/to_date are datetime.date objects.
    resolution_minutes: integer (1,5,15,60,...). For daily use a big value or 'D' mapping.
    Returns list of dicts: [{'timestamp': epoch, 'open':..., 'high':..., 'low':..., 'close':..., 'volume':...}, ...]
    """
    fyers = build_fyers_rest_client(client_id=client_id)
    # FYERS history payload sample (per docs):
    # data = {"symbol":"NSE:SBIN-EQ","resolution":"1","date_format":"1","range_from":"2023-08-01","range_to":"2023-08-16","cont_flag":"1"}
    res = []
    try:
        payload = {
            "symbol": symbol,
            "resolution": _api_resolution_from_minutes(resolution_minutes),
            "date_format": "1",  # returns epoch times in seconds
            "range_from": from_date.strftime("%Y-%m-%d"),
            "range_to": to_date.strftime("%Y-%m-%d"),
            "cont_flag": "1",
        }
        resp = fyers.history(payload)
        # FYERS returns dict like {'s':'ok','candles': [[ts, open, high, low, close, volume], ...]}
        if not resp:
            return res
        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except Exception:
                pass
        candles = resp.get("candles") if isinstance(resp, dict) else None
        if not candles:
            # try alternative keys
            candles = resp.get("data", {}).get("candles") if isinstance(resp, dict) else None
        if candles:
            for c in candles:
                # according to docs each candle: [timestamp, open, high, low, close, volume]
                try:
                    ts = int(c[0])
                    o = float(c[1])
                    h = float(c[2])
                    l = float(c[3])
                    cl = float(c[4])
                    vol = int(c[5])
                    rec = {"timestamp": ts, "open": o, "high": h, "low": l, "close": cl, "volume": vol}
                    res.append(rec)
                    if save_to_db and Candle is not None:
                        # upsert into Candle model (create or update)
                        try:
                            # adapt field names to your Candle model
                            Candle.objects.update_or_create(
                                symbol=symbol,
                                timestamp=ts,
                                defaults={"open": o, "high": h, "low": l, "close": cl, "volume": vol},
                            )
                        except Exception:
                            # avoid failing entire run because of DB row error
                            print("Candle save error for", symbol, ts)
                except Exception:
                    continue
    except Exception as e:
        print("fyers.history error:", str(e))
    return res
