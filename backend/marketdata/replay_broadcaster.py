# marketdata/replay_broadcaster.py
import asyncio
from datetime import datetime, timedelta, timezone
import re
from channels.layers import get_channel_layer
import motor.motor_asyncio  # Async MongoDB driver
from decouple import config

# MongoDB settings
MONGO_URI = config("MONGO_DB_URL", default="mongodb://localhost:27017")
DB_NAME = config("MONGO_DB_NAME", default="marketdata")
COLLECTION_NAME = "ticks"

# --- normalize instruments so they match frontend subscriptions ---
def _to_group_name(instrument: str) -> str:
    """
    Frontend subscribes with `NSE:{SYMBOL}-EQ`.
    Ensure DB instruments like 'RELIANCE' or 'NSE:RELIANCE' normalize to the same group.
    """
    inst = instrument.strip()
    if ":" not in inst:
        inst = f"NSE:{inst}"
    if "-" not in inst:
        inst = f"{inst}-EQ"
    # sanitize same as consumer
    return re.sub(r"[^a-zA-Z0-9\-_.]", "_", inst)

async def replay_loop():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    ticks_collection = db[COLLECTION_NAME]
    channel_layer = get_channel_layer()

    print("Starting 15-minute delay broadcaster (in-process)...")

    last_broadcast_time = datetime.now(timezone.utc) - timedelta(minutes=15)

    try:
        while True:
            start_time = last_broadcast_time
            end_time = datetime.now(timezone.utc) - timedelta(minutes=15)

            if start_time < end_time:
                cursor = (
                    ticks_collection
                    .find({"timestamp": {"$gt": start_time, "$lte": end_time}})
                    .sort("timestamp", 1)
                )

                async for tick in cursor:
                    group = _to_group_name(tick.get("instrument", ""))
                    if not group:
                        continue

                    # Make payload browser-friendly
                    val = dict(tick)
                    val["_id"] = str(val.get("_id", ""))
                    ts = val.get("timestamp")
                    if isinstance(ts, datetime):
                        val["timestamp"] = ts.isoformat()
                    val["type"] = "tick"

                    await channel_layer.group_send(
                        group,
                        {"type": "marketdata.message", "message": val},
                    )
                    # print(f"[broadcaster] → {group}")

                last_broadcast_time = end_time

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("Broadcaster stopped.")
    except Exception as e:
        import traceback
        print(f"Broadcaster error: {e}\n{traceback.format_exc()}")

# Singleton task control so we only start once per process
_broadcaster_task = None
_task_lock = asyncio.Lock()

async def ensure_broadcaster_running():
    global _broadcaster_task
    async with _task_lock:
        if _broadcaster_task is None or _broadcaster_task.done():
            _broadcaster_task = asyncio.create_task(replay_loop())
            print("Broadcaster task started in-process.")

# --- Management command still supported (optional) ---
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Broadcasts 15-minute delayed market data via Channels (async Motor version)"

    def handle(self, *args, **options):
        asyncio.run(replay_loop())
