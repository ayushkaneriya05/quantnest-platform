# backend/marketdata/management/commands/fyers_ingest.py
from django.core.management.base import BaseCommand
from django.conf import settings
from fyers_apiv3 import fyersModel
from marketdata.models import MarketDataToken
from marketdata.mongo_client import get_ticks_collection
import time
from datetime import datetime, timezone
import json
from pathlib import Path
import os

# Load nifty100 symbols
nifty100_path = Path(settings.BASE_DIR) / 'data' / 'nifty100_symbols.json'
nifty100_data = json.loads(nifty100_path.read_text())

class Command(BaseCommand):
    help = 'Starts the Fyers WebSocket for live data ingestion into MongoDB'

    def handle(self, *args, **options):
        client_id = settings.FYERS_CLIENT_ID
        token_row = MarketDataToken.objects.get(pk=1)
        access_token = token_row.access_token

        if not access_token or not token_row.is_valid():
            self.stdout.write(self.style.ERROR('Fyers token is invalid. Please log in.'))
            return

        ticks_collection = get_ticks_collection()
        nifty_100_symbols = ["NSE:" + s['symbol'] + "-EQ" for s in nifty100_data]

        def on_ticks(ticks):
            documents = []
            for tick in ticks:
                documents.append({
                    "instrument": tick['symbol'],
                    "timestamp": datetime.fromtimestamp(tick['timestamp'], tz=timezone.utc),
                    "price": tick['ltp'],
                    "volume": tick.get('vtt', 0) # Volume Till Trade
                })

            if documents:
                try:
                    ticks_collection.insert_many(documents)
                    self.stdout.write(f"Inserted {len(documents)} ticks into MongoDB.")
                except Exception as e:
                    self.stderr.write(f"Error inserting ticks to MongoDB: {e}")

        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path=os.path.join(settings.BASE_DIR, 'logs'))
        fyers.websocket(data_type="symbolData", symbols=nifty_100_symbols, on_message=on_ticks)

        self.stdout.write("Fyers WebSocket connected. Ingesting ticks...")
        while True:
            time.sleep(1)