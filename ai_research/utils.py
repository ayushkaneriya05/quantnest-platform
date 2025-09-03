# utils.py
import os
from pathlib import Path
import json

import logging
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

LOG = logging.getLogger("ai_research")
logging.basicConfig(level=logging.INFO)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "quantnest_marketdata")
SCRAPER_DELAY_SECONDS = int(os.getenv("SCRAPER_DELAY_SECONDS", "3"))
SNAPSHOT_FRESHNESS_MINUTES = int(os.getenv("SNAPSHOT_FRESHNESS_MINUTES", "30"))

BASE_DIR = Path(__file__).resolve().parent
nifty100_path = BASE_DIR / "data" /"nifty100_symbols.json"
nifty100_data = json.loads(nifty100_path.read_text())
WATCHLIST = [f"{s['symbol']}" for s in nifty100_data]

if not MONGO_URI:
    LOG.error("MONGO_URI not set. Set in .env file")

def get_db():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]
