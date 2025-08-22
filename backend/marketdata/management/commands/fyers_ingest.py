import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.conf import settings

# Use the data_ws module for market data as per the latest fyers_apiv3 docs
from fyers_apiv3.FyersWebsocket import data_ws 
from marketdata.utils import get_active_fyers_access_token
from marketdata.mongo_client import get_ticks_collection

# Setup a dedicated logger for this ingestion script
logger = logging.getLogger(__name__)

# --- Load Nifty 100 Symbols ---
try:
    # Build the path to the data file relative to the project's base directory
    nifty100_path = Path(settings.BASE_DIR) / 'data' / 'nifty100_symbols.json'
    nifty100_data = json.loads(nifty100_path.read_text())
except FileNotFoundError:
    nifty100_data = []
    logger.error("FATAL: nifty100_symbols.json not found in the 'data' directory. The service cannot start.")

class Command(BaseCommand):
    help = 'Starts the Fyers WebSocket for live data ingestion into MongoDB (Full Data Mode).'

    def handle(self, *args, **options):
        if not nifty100_data:
            self.stderr.write(self.style.ERROR("Cannot start ingestion: nifty100_symbols.json is missing or empty."))
            return

        client_id = settings.FYERS_CLIENT_ID
        
        access_token = get_active_fyers_access_token()
        if not access_token:
            raise RuntimeError("No valid Fyers access token available")


        # Prepare the correctly formatted access token for the websocket
        # Format required by the SDK is: <CLIENT_ID>:<ACCESS_TOKEN>
        websocket_token = f"{client_id}:{access_token}"

        # Prepare the list of symbols for subscription
        nifty_100_symbols = [f"NSE:{s['symbol']}-EQ" for s in nifty100_data]
        self.stdout.write(f"Preparing to subscribe to {len(nifty_100_symbols)} symbols in full data mode.")

        # --- WebSocket Callback Functions ---

        def on_message(tick):
            """
            Callback to process incoming messages from the WebSocket.
            This now correctly handles a single dictionary per message.
            """
            if not isinstance(tick, dict):
                logger.info(f"Received non-tick (control/status) message from WebSocket: {tick}")
                return # Ignore this message and continue

            ticks_collection = get_ticks_collection()
            
            try:
                # Map all the fields from the sample response to a new document
                document_to_insert = {
                    "instrument": tick.get('symbol'),
                    "timestamp": datetime.fromtimestamp(tick.get('last_traded_time'), tz=timezone.utc),
                    "price": tick.get('ltp'),
                    "volume_traded_today": tick.get('vol_traded_today'),
                    "last_traded_qty": tick.get('last_traded_qty'),
                    "avg_trade_price": tick.get('avg_trade_price'),
                    "open": tick.get('open_price'),
                    "high": tick.get('high_price'),
                    "low": tick.get('low_price'),
                    "close": tick.get('prev_close_price'),
                    "change": tick.get('ch'),
                    "change_percent": tick.get('chp')
                }
                
                # Insert the single document into MongoDB
                # ticks_collection.update_one({"instrument": tick.get('symbol'),"timestamp": datetime.fromtimestamp(tick.get('last_traded_time'), tz=timezone.utc)},{"$set":document_to_insert} ,upsert=True)
                ticks_collection.insert_one(document_to_insert)
                logger.info(f"Insert tick for {tick.get('symbol')} @ {tick.get('ltp')}")

            except Exception as e:
                logger.error(f"Error processing a single full-mode tick: {tick}. Error: {e}")

        def on_connect():
            """
            Callback for when the WebSocket connection is established.
            Subscribes to the symbols list.
            """
            self.stdout.write(self.style.SUCCESS("✅ Fyers WebSocket connected successfully."))
            self.stdout.write("Subscribing to Nifty 100 symbols...")
            fyers_socket.subscribe(symbols=nifty_100_symbols)

        def on_close(message):
            logger.warning(f"WebSocket connection closed: {message}")

        def on_error(message):
            """
            Callback when WebSocket receives an error.
            If the token is expired, refresh it and reconnect.
            """
            logger.error(f"WebSocket error received: {message}")
            
            # Check if the error is a token expiration
            if isinstance(message, dict) and message.get('code') == -99 and message.get('message') == "Token is expired":
                self.stderr.write(self.style.WARNING("Fyers access token expired. Refreshing token..."))
                
                # Refresh access token
                new_access_token = get_active_fyers_access_token(force_refresh=True)
                if not new_access_token:
                    self.stderr.write(self.style.ERROR("Failed to refresh Fyers access token. Exiting."))
                    fyers_socket.close()
                    return
                
                # Update the websocket token
                fyers_socket.access_token = f"{client_id}:{new_access_token}"
                self.stdout.write(self.style.SUCCESS("Reconnecting WebSocket with refreshed token..."))
                
                # Reconnect
                fyers_socket.connect()


        # --- Initialize and Connect WebSocket ---
        fyers_socket = data_ws.FyersDataSocket(
            access_token=websocket_token,
            log_path=os.path.join(settings.BASE_DIR, 'logs/'),
            litemode=False, 
            write_to_file=False,
            reconnect=True, 
            on_connect=on_connect,
            on_close=on_close,
            on_error=on_error,
            on_message=on_message 
        )

        self.stdout.write("Attempting to connect to Fyers WebSocket...")
        fyers_socket.connect()

        self.stdout.write(self.style.SUCCESS("🚀 Ingestion engine is now running. Press Ctrl+C to stop."))
        while True:
            time.sleep(1)