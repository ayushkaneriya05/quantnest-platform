# backend/marketdata/management/commands/run_marketdata_gateway.py
import json
import logging
import time
import threading
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from dateutil.parser import isoparse

from marketdata.fyers_ws_client import FyersWebsocketClient
from marketdata.storage import FyersTokenStorage
from marketdata.models import LiveTick

logger = logging.getLogger(__name__)

# The delay for broadcasting market data
DATA_DELAY = timedelta(minutes=15)

def broadcast_delayed_data():
    """
    This function runs in a separate thread. It periodically queries the database
    for ticks that are older than the specified delay and broadcasts them.
    """
    channel_layer = get_channel_layer()
    
    while True:
        try:
            # Calculate the cutoff time for the 15-minute delay
            cutoff_time = datetime.now(timezone.utc) - DATA_DELAY
            
            # Find all ticks that are ready to be broadcasted
            ticks_to_broadcast = LiveTick.objects.filter(timestamp__lte=cutoff_time).order_by('timestamp')

            if ticks_to_broadcast.exists():
                with transaction.atomic():
                    # Lock the selected rows to prevent race conditions
                    processed_ticks = list(ticks_to_broadcast.select_for_update(skip_locked=True))
                    
                    if processed_ticks:
                        logger.info(f"Broadcasting {len(processed_ticks)} delayed ticks.")
                        
                        # Broadcast each tick to the 'marketdata' group
                        for tick in processed_ticks:
                            async_to_sync(channel_layer.group_send)(
                                "marketdata",
                                {
                                    "type": "market_data_message",
                                    "message": {
                                        "symbol": tick.symbol,
                                        "ts": tick.timestamp.timestamp(),
                                        "payload": tick.payload,
                                    },
                                },
                            )
                        
                        # Delete the broadcasted ticks to keep the table small
                        tick_ids_to_delete = [t.id for t in processed_ticks]
                        LiveTick.objects.filter(id__in=tick_ids_to_delete).delete()

        except Exception as e:
            logger.error(f"Error in broadcast thread: {e}")
        
        # Wait for a few seconds before the next check
        time.sleep(5)


class Command(BaseCommand):
    help = "Runs the Fyers market data gateway, stores live data, and broadcasts it with a 15-minute delay."

    def handle(self, *args, **options):
        self.stdout.write("Starting Fyers market data gateway...")

        token_storage = FyersTokenStorage()
        access_token = token_storage.get_token()

        if not access_token:
            self.stderr.write("Fyers access token not found. Please generate it first by running 'run_fyers_client.py'.")
            return

        # Start the delayed data broadcaster in a background thread
        broadcaster_thread = threading.Thread(target=broadcast_delayed_data, daemon=True)
        broadcaster_thread.start()
        self.stdout.write("Delayed data broadcaster thread started.")

        def on_message(message):
            """Callback to handle incoming ticks from the Fyers WebSocket."""
            try:
                # Create LiveTick objects in bulk for efficiency
                ticks_to_create = []
                for tick_data in message:
                    if tick_data.get('symbol') and tick_data.get('ltp'):
                        ticks_to_create.append(
                            LiveTick(
                                symbol=tick_data['symbol'],
                                timestamp=datetime.fromtimestamp(tick_data['timestamp'], tz=timezone.utc),
                                payload=tick_data
                            )
                        )
                
                if ticks_to_create:
                    LiveTick.objects.bulk_create(ticks_to_create)
                    logger.debug(f"Stored {len(ticks_to_create)} new ticks in the database.")

            except Exception as e:
                logger.error(f"Error storing tick data: {e}")

        def on_open():
            """Callback for when the WebSocket connection is established."""
            try:
                # Load symbols from the JSON file to subscribe
                with open('backend/data/nifty500_symbols.json', 'r') as f:
                    symbols_to_subscribe = [item['symbol'] for item in json.load(f)]
                
                # Subscribe in batches
                batch_size = 100
                for i in range(0, len(symbols_to_subscribe), batch_size):
                    batch = symbols_to_subscribe[i:i + batch_size]
                    ws_client.subscribe(symbols=batch)
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error during symbol subscription: {e}")

        # Initialize and connect the WebSocket client
        ws_client = FyersWebsocketClient(on_message=on_message, on_open=on_open)
        ws_client.connect(access_token)

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("Stopping Fyers market data gateway...")
            ws_client.close()
            self.stdout.write("Gateway stopped.")