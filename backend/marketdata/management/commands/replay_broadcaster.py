# backend/marketdata/management/commands/replay_broadcaster.py
import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from marketdata.mongo_client import get_ticks_collection

class Command(BaseCommand):
    help = 'Broadcasts 15-minute delayed market data via Channels'

    async def handle_async(self):
        channel_layer = get_channel_layer()
        ticks_collection = get_ticks_collection()
        self.stdout.write("Starting 15-minute delay broadcaster...")

        last_broadcast_time = timezone.now() - timedelta(minutes=15)

        while True:
            start_time = last_broadcast_time
            end_time = timezone.now() - timedelta(minutes=15)

            if start_time < end_time:
                # Find ticks in the 15-minute delayed window
                ticks_to_broadcast = ticks_collection.find({
                    "timestamp": {
                        "$gt": start_time,
                        "$lte": end_time
                    }
                }).sort("timestamp", 1)

                for tick in ticks_to_broadcast:
                    instrument_group = tick['instrument'].replace(':', '_').replace('-', '_') # Sanitize for group name
                    
                    # Convert ObjectId and datetime for JSON serialization
                    tick['_id'] = str(tick['_id'])
                    tick['timestamp'] = tick['timestamp'].isoformat()
                    
                    await channel_layer.group_send(
                        instrument_group,
                        {
                            "type": "marketdata.message",
                            "message": tick,
                        }
                    )
                last_broadcast_time = end_time

            await asyncio.sleep(1) # Check for new ticks every second

    def handle(self, *args, **options):
        asyncio.run(self.handle_async())