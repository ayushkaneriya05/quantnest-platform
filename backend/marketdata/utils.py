# utils.py
import hashlib
import requests
import logging
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.utils.timezone import now
from .models import MarketDataToken
import pytz

logger = logging.getLogger(__name__)
ist = pytz.timezone("Asia/Kolkata")

today_eod = datetime.now(ist).replace(hour=23, minute=59, second=59, microsecond=0)


def refresh_fyers_token(token_row: MarketDataToken) -> bool:
    """Refreshes the Fyers access token using the stored refresh_token (v3 flow)."""
    if not token_row.refresh_token:
        logger.error("No refresh_token available in MarketDataToken row")
        return False

    client_id = getattr(settings, "FYERS_CLIENT_ID", None)
    secret_key = getattr(settings, "FYERS_SECRET", None)
    pin = getattr(settings, "FYERS_PIN", None)

    if not client_id or not secret_key or not pin:
        logger.error("Fyers credentials (client_id, secret_key, pin) not configured")
        return False

    # Compute SHA256(client_id:secret_key)
    app_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()

    url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
    payload = {
        "grant_type": "refresh_token",
        "appIdHash": app_hash,
        "refresh_token": token_row.refresh_token,
        "pin": pin,
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(resp)
        data = resp.json()
    except Exception as exc:
        logger.exception("Error refreshing token: %s", exc)
        return False

    if data.get("s") != "ok":
        logger.error("Token refresh failed: %s", data)
        return False

    # Update token row
    token_row.access_token = data.get("access_token")
    token_row.refresh_token = data.get("refresh_token") or token_row.refresh_token
    expires_in = data.get("expires_in")
    token_row.expires_at = today_eod
    if expires_in:
        try:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            token_row.expires_at = None

    token_row.save()
    logger.info("Fyers token refreshed successfully")
    return True


def get_active_fyers_access_token(force_refresh=False):
    """Get a valid Fyers access token, refreshing if needed."""
    token_row = MarketDataToken.objects.filter(is_active=True).first()
    if not token_row:
        return None

    # If forced refresh
    if force_refresh:
        if refresh_fyers_token(token_row):
            return token_row.access_token
        return None

    # If expired → refresh
    if token_row.expires_at and token_row.expires_at < now():
        refreshed = refresh_fyers_token(token_row)
        if refreshed:
            return MarketDataToken.objects.filter(is_active=True).first().access_token
        return None

    return token_row.access_token
