# backend/marketdata/utils.py
from datetime import datetime, timezone

def iso_to_epoch_seconds(iso_ts: str) -> int:
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

# marketdata/utils.py
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from marketdata.models import MarketDataToken

def get_active_fyers_access_token():
    """
    Returns the latest active Fyers access token stored in DB.
    Falls back gracefully if no valid token is found.
    """
    try:
        token_entry = MarketDataToken.objects.filter(
            is_active=True, expires_at__gt=timezone.now()
        ).latest("created_at")
        return token_entry.access_token
    except ObjectDoesNotExist:
        raise Exception("No valid Fyers access token found in DB.")
    except Exception as e:
        raise Exception(f"Error fetching Fyers token: {str(e)}")

