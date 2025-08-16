# backend/marketdata/utils.py
from datetime import datetime, timezone

def iso_to_epoch_seconds(iso_ts: str) -> int:
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())
