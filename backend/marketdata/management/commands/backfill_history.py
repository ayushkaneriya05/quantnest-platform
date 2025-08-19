import time
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta,timezone 

from django.core.management.base import BaseCommand
from django.conf import settings

from fyers_apiv3 import fyersModel
from marketdata.models import MarketDataToken
from marketdata.mongo_client import get_candles_collection
from pymongo import UpdateOne

# Setup a dedicated logger for this backfill script
logger = logging.getLogger(__name__)

# --- Load Nifty 100 Symbols ---
try:
    nifty100_path = Path(settings.BASE_DIR) / 'data' / 'nifty100_symbols.json'
    nifty100_data = json.loads(nifty100_path.read_text())
except FileNotFoundError:
    nifty100_data = []
    logger.error("FATAL: nifty100_symbols.json not found. Cannot start backfill.")

class Command(BaseCommand):
    help = 'Fetches historical 1-minute candle data for Nifty 100 stocks in chunks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=365,
            help='Number of days of historical data to backfill.'
        )

    def handle(self, *args, **options):
        if not nifty100_data:
            self.stderr.write(self.style.ERROR("Cannot start backfill: nifty100_symbols.json is missing or empty."))
            return

        days_to_backfill = options['days']
        self.stdout.write(self.style.SUCCESS(f"🚀 Starting historical data backfill for the last {days_to_backfill} days."))

        client_id = settings.FYERS_CLIENT_ID
        try:
            token_row = MarketDataToken.objects.get(pk=1)
            access_token = token_row.access_token
        except MarketDataToken.DoesNotExist:
            self.stderr.write(self.style.ERROR("No MarketDataToken found. Please log in first."))
            return

        if not access_token or not token_row.is_valid():
            self.stderr.write(self.style.ERROR('Fyers access token is invalid or expired.'))
            return
        
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path=os.path.join(settings.BASE_DIR, 'logs/'))
        candles_collection = get_candles_collection()

        # ** FIX: Break the date range into smaller chunks (e.g., 90 days) **
        total_start_date = (datetime.now(timezone.utc) - timedelta(days=days_to_backfill)).date()
        today = datetime.now(timezone.utc).date()
        
        nifty_100_symbols = [f"NSE:{s['symbol']}-EQ" for s in nifty100_data]

        for i, symbol in enumerate(nifty_100_symbols):
            self.stdout.write(f"\n[{i+1}/{len(nifty_100_symbols)}] Processing {symbol}...")
            
            # Loop through the date range in 90-day chunks
            chunk_start_date = total_start_date
            while chunk_start_date < today:
                chunk_end_date = chunk_start_date + timedelta(days=90)
                if chunk_end_date >= today:
                    chunk_end_date = today - timedelta(days=1)

                self.stdout.write(f"  Fetching from {chunk_start_date} to {chunk_end_date}...")

                try:
                    data = {
                        "symbol": symbol,
                        "resolution": "1",
                        "date_format": "1",
                        "range_from": chunk_start_date.strftime("%Y-%m-%d"),
                        "range_to": chunk_end_date.strftime("%Y-%m-%d"),
                        "cont_flag": "1"
                    }

                    response = fyers.history(data=data)

                    if response.get("s") != "ok" or not response.get("candles"):
                        self.stderr.write(self.style.WARNING(f"    - Could not fetch data for {symbol} in this range: {response.get('message', 'No candles returned')}"))
                    else:
                        candles_to_insert = [
                            {
                                "instrument": symbol, "timestamp": datetime.fromtimestamp(c[0], tz=timezone.utc),
                                "resolution": "1m", "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]
                            } for c in response["candles"]
                        ]
                        
                        if candles_to_insert:
                            operations = [
                                UpdateOne({"instrument": c["instrument"], "timestamp": c["timestamp"], "resolution": c["resolution"]}, {"$set": c}, upsert=True)
                                for c in candles_to_insert
                            ]
                            result = candles_collection.bulk_write(operations)
                            self.stdout.write(self.style.SUCCESS(f"    -> Synced {result.upserted_count + result.modified_count} candles."))
                    
                    # API rate limit delay is crucial
                    time.sleep(0.5)

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"    -> An unexpected error occurred: {e}"))
                    time.sleep(2) # Wait longer on error
                
                # Move to the next chunk
                chunk_start_date = chunk_end_date + timedelta(days=1)

        self.stdout.write(self.style.SUCCESS("\n✅ Historical data backfill complete!"))