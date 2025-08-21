# backend/marketdata/management/commands/replay_broadcaster.py
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
import motor.motor_asyncio  # Async MongoDB driver
from decouple import config
# MongoDB settings
MONGO_URI = config("MONGO_DB_URL", default="mongodb://localhost:27017")
DB_NAME = config("MONGO_DB_NAME", default="marketdata")
COLLECTION_NAME = "ticks"

class Command(BaseCommand):
    help = "Broadcasts 15-minute delayed market data via Channels (async Motor version)"

    async def handle_async(self):
        # Setup MongoDB async client
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        ticks_collection = db[COLLECTION_NAME]

        channel_layer = get_channel_layer()
        self.stdout.write(self.style.SUCCESS("Starting 15-minute delay broadcaster..."))

        # Start 15 minutes behind current time
        last_broadcast_time = datetime.now(timezone.utc) - timedelta(minutes=15)

        try:
            while True:
                start_time = last_broadcast_time
                end_time = datetime.now(timezone.utc) - timedelta(minutes=15)

                if start_time < end_time:
                    # Async find query, sorted by timestamp
                    cursor = ticks_collection.find(
                        {"timestamp": {"$gt": start_time, "$lte": end_time}}
                    ).sort("timestamp", 1)

                    async for tick in cursor:
                        # Hash instrument name to match consumer groups
                        instrument_group = hashlib.sha1(
                            tick["instrument"].encode()
                        ).hexdigest()

                        # Serialize fields for JSON
                        tick["_id"] = str(tick["_id"])
                        if isinstance(tick["timestamp"], datetime):
                            tick["timestamp"] = tick["timestamp"].isoformat()
                        tick['type'] = "tick"
                        # Broadcast to group
                        await channel_layer.group_send(
                            instrument_group,
                            {
                                "type": "marketdata.message",
                                "message": tick,
                            },
                        )

                    last_broadcast_time = end_time

                await asyncio.sleep(1)  # sleep 1 second before next check

        except asyncio.CancelledError:
            self.stdout.write(self.style.WARNING("Broadcaster stopped."))
        except Exception as e:
            import traceback

            self.stderr.write(self.style.ERROR(f"Error: {e}\n{traceback.format_exc()}"))

    def handle(self, *args, **options):
        asyncio.run(self.handle_async())
