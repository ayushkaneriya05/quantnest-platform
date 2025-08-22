# backend/marketdata/management/commands/aggregate_candles.py
from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime,timedelta , timezone
from marketdata.mongo_client import get_ticks_collection, get_candles_collection

def aggregate_job():
    print("Running 1-minute candle aggregation job...")
    ticks_collection = get_ticks_collection()
    candles_collection = get_candles_collection()

    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(minutes=1)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": one_minute_ago, "$lt": now}}},
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": {
                "instrument": "$instrument",
                "timestamp": {"$dateTrunc": {"date": "$timestamp", "unit": "minute"}}
            },
            "open": {"$first": "$price"},
            "high": {"$max": "$price"},
            "low": {"$min": "$price"},
            "close": {"$last": "$price"},
            "volume": {"$sum": "$volume"}
        }},
        {"$project": {
            "_id": 0,
            "instrument": "$_id.instrument",
            "timestamp": "$_id.timestamp",
            "resolution": "1m",
            "open": "$open",
            "high": "$high",
            "low": "$low",
            "close": "$close",
            "volume": "$volume"
        }}
    ]
    
    new_candles = list(ticks_collection.aggregate(pipeline))
    if new_candles:
        for candle in new_candles:
            candles_collection.update_one(
                {"instrument": candle["instrument"], "timestamp": candle["timestamp"], "resolution": "1m"},
                {"$set": candle},
                upsert=True
            )
        print(f"Upserted {len(new_candles)} 1-minute candles.")


class Command(BaseCommand):
    help = 'Starts the candle aggregation scheduler'
    def handle(self, *args, **options):
        scheduler = BlockingScheduler()
        scheduler.add_job(aggregate_job, 'cron', second='5')
        self.stdout.write("Starting candle aggregation scheduler...")
        scheduler.start()