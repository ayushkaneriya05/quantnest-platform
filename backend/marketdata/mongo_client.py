# backend/marketdata/mongo_client.py
from pymongo import MongoClient
from django.conf import settings

_client = None

def get_mongo_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_DB_URL)
    return _client

def get_db():
    client = get_mongo_client()
    return client[settings.MONGO_DB_NAME]

def get_ticks_collection():
    db = get_db()
    return db.ticks

def get_candles_collection():
    db = get_db()
    # Create indexes for efficient querying
    db.candles.create_index([("instrument", 1), ("timestamp", -1), ("resolution", 1)], unique=True)
    return db.candles