# backend/ohlc/backfill.py
import os, time, math, json
import httpx
from celery import shared_task
from datetime import datetime, timezone
from .models import OHLC

FYERS_API_BASE = os.getenv("FYERS_API_BASE", "https://api.fyers.in")
FYERS_API_KEY = os.getenv("FYERS_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# NOTE: adapt endpoints to actual Fyers v3 docs / auth flow.
# This is a conservative skeleton that loops symbols and respects rate limits.

@shared_task(bind=True)
def backfill_1m_for_symbols(self, symbols, start_date=None, end_date=None, per_symbol_rate_limit=0.5):
    """
    Backfill 1m candles for the provided symbol list from Fyers REST.
    - symbols: list of instrument identifiers that Fyers expects (eg. 'NSE:RELIANCE- EQ' or similar)
    - start_date / end_date: ISO strings. If None, Fyers default applies.
    - per_symbol_rate_limit: seconds to sleep between symbol calls (avoid 429).
    """
    headers = {"Authorization": f"Bearer {FYERS_API_KEY}"} if FYERS_API_KEY else {}
    client = httpx.Client(timeout=30)

    inserted_total = 0
    for sym in symbols:
        try:
            # build URL (adapt to Fyers docs)
            # Example placeholder: /data/v1/history?symbol={sym}&resolution=1&from=...&to=...
            params = {}
            if start_date:
                params["from"] = start_date
            if end_date:
                params["to"] = end_date
            params["resolution"] = "1"  # 1 minute
            url = f"{FYERS_API_BASE}/v1/history/{sym}"
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                # handle throttle / backoff
                time.sleep(per_symbol_rate_limit)
                continue
            payload = resp.json()
            # adapt payload parsing: assume payload contains arrays of timestamps, o,h,l,c,v
            # Replace below with actual response shape
            timestamps = payload.get("t", [])
            opens = payload.get("o", [])
            highs = payload.get("h", [])
            lows = payload.get("l", [])
            closes = payload.get("c", [])
            volumes = payload.get("v", [])
            objs = []
            for i, ts in enumerate(timestamps):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                objs.append(OHLC(symbol=sym, tf="1m", ts=dt, open=opens[i], high=highs[i], low=lows[i], close=closes[i], volume=volumes[i]))
            if objs:
                OHLC.objects.bulk_create(objs, ignore_conflicts=True)
                inserted_total += len(objs)
            # sleep to avoid rapid calls
            time.sleep(per_symbol_rate_limit)
        except Exception as e:
            # log and continue
            import logging
            logging.exception("Backfill error for %s: %s", sym, e)
            time.sleep(per_symbol_rate_limit)
            continue
    return {"inserted_total": inserted_total}
