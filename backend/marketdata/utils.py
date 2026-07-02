# utils.py
import hashlib
import requests
import logging
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now
from .models import MarketDataToken
import pytz

logger = logging.getLogger(__name__)
ist = pytz.timezone("Asia/Kolkata")


def _get_today_eod():
    """Returns today's 23:59:59 IST. Called dynamically to avoid stale dates after midnight."""
    return datetime.now(ist).replace(hour=23, minute=59, second=59, microsecond=0)


def _get_token_row():
    """Standardized singleton lookup — always uses pk=1 to avoid is_active inconsistency."""
    obj, _ = MarketDataToken.objects.get_or_create(pk=1)
    return obj


def refresh_fyers_token(token_row: MarketDataToken) -> bool:
    """
    Attempts to refresh the Fyers access token using the stored refresh_token (v3 flow).

    NOTE: As of 2025, SEBI regulations have disabled the refresh token API on Fyers.
    This function will likely always fail. The admin must re-login daily via /fyers/login/.
    It is kept for forward-compatibility in case Fyers re-enables the API.
    """
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
        data = resp.json()
    except Exception as exc:
        logger.exception("Error refreshing token: %s", exc)
        return False

    if data.get("s") != "ok":
        logger.error(
            "Token refresh failed (code=%s): %s. Admin must re-login via /fyers/login/.",
            data.get("code"),
            data.get("message", data),
        )
        return False

    # Update token row
    token_row.access_token = data.get("access_token")
    token_row.refresh_token = data.get("refresh_token") or token_row.refresh_token
    expires_in = data.get("expires_in")
    token_row.expires_at = _get_today_eod()
    if expires_in:
        try:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            token_row.expires_at = _get_today_eod()

    token_row.save()
    logger.info("Fyers token refreshed successfully")
    return True


def get_active_fyers_access_token(force_refresh=False):
    """Get a valid Fyers access token, attempting refresh if expired.

    Uses a cache lock to prevent multiple concurrent refresh attempts
    from hammering the Fyers API simultaneously.
    """
    token_row = _get_token_row()
    if not token_row.access_token:
        return None

    # If forced refresh
    if force_refresh:
        if refresh_fyers_token(token_row):
            return token_row.access_token
        return None

    # If expired → attempt refresh (with lock to prevent thundering herd)
    if token_row.expires_at and token_row.expires_at < now():
        lock_key = "fyers_token_refresh_lock"
        if cache.add(lock_key, True, timeout=30):  # 30-second lock
            try:
                if refresh_fyers_token(token_row):
                    return token_row.access_token
            finally:
                cache.delete(lock_key)
        else:
            # Another thread is already refreshing — re-read from DB
            token_row.refresh_from_db()
            if token_row.is_valid():
                return token_row.access_token
        return None

    return token_row.access_token
