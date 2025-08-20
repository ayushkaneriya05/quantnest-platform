# backend/marketdata/management/commands/replay_broadcaster.py
import asyncio
import hashlib
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta, timezone
from channels.layers import get_channel_layer
from marketdata.mongo_client import get_ticks_collection

class Command(BaseCommand):
    help = 'Broadcasts 15-minute delayed market data via Channels'

    async def handle_async(self):
        channel_layer = get_channel_layer()
        ticks_collection = get_ticks_collection()
        self.stdout.write(self.style.SUCCESS("Starting 15-minute delay broadcaster..."))

        last_broadcast_time = datetime.now(timezone.utc) - timedelta(minutes=15)

        try:
            while True:
                start_time = last_broadcast_time
                end_time = datetime.now(timezone.utc) - timedelta(minutes=15)

                if start_time < end_time:
                    # Query ticks with index
                    ticks_to_broadcast = ticks_collection.find(
                        {"timestamp": {"$gt": start_time, "$lte": end_time}}
                    ).sort("timestamp", 1)

                    for tick in ticks_to_broadcast:  # if using Motor
                        # Safe group name
                        instrument_group = hashlib.sha1(
                            tick['instrument'].encode()
                        ).hexdigest()

                        # Serialize fields
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

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.stdout.write(self.style.WARNING("Broadcaster stopped."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))

    def handle(self, *args, **options):
        asyncio.run(self.handle_async())
