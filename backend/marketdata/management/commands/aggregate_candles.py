import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from django.core.management.base import BaseCommand
from django.conf import settings
from fyers_apiv3 import fyersModel

from marketdata.mongo_client import get_candles_collection
from marketdata.utils import get_active_fyers_access_token

logger = logging.getLogger(__name__)

# Load Nifty 100 symbols
try:
    # Build the path to the data file relative to the project's base directory
    nifty100_path = Path(settings.BASE_DIR) / 'data' / 'nifty100_symbols.json'
    nifty100_data = json.loads(nifty100_path.read_text())
except FileNotFoundError:
    nifty100_data = []
    logger.error("FATAL: nifty100_symbols.json not found in the 'data' directory. The service cannot start.")

# Convert into Fyers format: NSE:<symbol>-EQ
symbol_list = [f"NSE:{s['symbol']}-EQ" for s in nifty100_data]


def fetch_and_store_candles():
    print("Fetching 1-minute candles for Nifty 100 from Fyers API...")

    access_token = get_active_fyers_access_token()
    if not access_token:
        print("No valid Fyers access token")
        return

    fyers = fyersModel.FyersModel(
        client_id=settings.FYERS_CLIENT_ID,
        token=access_token,
        log_path=os.path.join(settings.BASE_DIR, 'logs/')
    )

    candles_collection = get_candles_collection()
    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(minutes=1)

    for symbol in symbol_list:
        data = {
            "symbol": symbol,
            "resolution": "1",   # 1-minute candles
            "date_format": "0",  # epoch timestamps
            "range_from": int(one_minute_ago.timestamp()),
            "range_to": int(now.timestamp()),
            "cont_flag": "1"
        }

        try:
            resp = fyers.history(data)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            continue
        if resp.get("s") != "ok":
            print(f"Fyers API error for {symbol}: {resp}")
            continue

        candles = resp.get("candles", [])
        for c in candles:
            ts, o, h, l, close, vol = c
            candle_doc = {
                "instrument": symbol,
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                "resolution": "1m",
                "open": o,
                "high": h,
                "low": l,
                "close": close,
                "volume": vol
            }
            candles_collection.update_one(
                {"instrument": symbol, "timestamp": candle_doc["timestamp"], "resolution": "1m"},
                {"$set": candle_doc},
                upsert=True
            )
        if candles:
            print(f"Upserted {len(candles)} candles for {symbol}")


class Command(BaseCommand):
    help = 'Fetches 1-minute candles for Nifty 100 stocks from Fyers API'

    def handle(self, *args, **options):
        scheduler = BlockingScheduler()
        # Run every minute at 5 seconds (after the candle closes)
        scheduler.add_job(fetch_and_store_candles, 'cron', second='5')
        self.stdout.write("Starting Nifty100 candle fetch scheduler...")
        scheduler.start()
