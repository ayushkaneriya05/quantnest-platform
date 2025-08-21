# utils.py
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.utils.timezone import now
from .models import MarketDataToken
import logging

logger = logging.getLogger(__name__)

try:
    from fyers_apiv3 import fyersModel
except ImportError:
    fyersModel = None


def refresh_fyers_token(token_row: MarketDataToken) -> bool:
    """Refreshes the fyers access token using the stored refresh_token."""
    if fyersModel is None:
        logger.error("fyers_apiv3 not installed on server")
        return False

    if not token_row.refresh_token:
        logger.error("No refresh_token available in MarketDataToken row")
        return False

    client_id = getattr(settings, "FYERS_CLIENT_ID", None)
    secret_key = getattr(settings, "FYERS_SECRET", None)
    redirect_uri = getattr(settings, "FYERS_REDIRECT_URI", None)
    if not client_id or not secret_key or not redirect_uri:
        logger.error("Fyers credentials not configured")
        return False

    try:
        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="refresh_token"
        )
        session.set_token(token_row.refresh_token)
        resp = session.generate_token()
    except Exception as exc:
        logger.exception("Error refreshing token: %s", exc)
        return False

    # Update token row
    token_row.access_token = resp.get("access_token") or resp.get("accessToken")
    token_row.refresh_token = resp.get("refresh_token") or resp.get("refreshToken")
    expires_in = resp.get("expires_in") or resp.get("expiresIn") or None
    if expires_in:
        try:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            token_row.expires_at = None
    else:
        token_row.expires_at = None
    token_row.save()
    return True


def get_active_fyers_access_token():
    """Get a valid Fyers access token, refreshing if needed."""
    token_row = MarketDataToken.objects.filter(is_active=True).first()
    if not token_row:
        return None

    # If expired → refresh
    if token_row.expires_at and token_row.expires_at < now():
        refreshed = refresh_fyers_token(token_row)
        if refreshed:
            return MarketDataToken.objects.filter(is_active=True).first().access_token
        return None

    return token_row.access_token
