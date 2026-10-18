from datetime import datetime
from zoneinfo import ZoneInfo

from .models import MarketDataToken

ist = ZoneInfo("Asia/Kolkata")


def _get_today_eod():
    """Calculate the daily access-token expiry in the market timezone."""
    return datetime.now(ist).replace(hour=23, minute=59, second=59, microsecond=0)


def _get_token_row():
    """Return the singleton used by market-data sign-in and status."""
    token, _ = MarketDataToken.objects.get_or_create(pk=1)
    return token


def get_active_fyers_access_token():
    """Return a valid stored token; expired tokens require a fresh admin sign-in."""
    token = MarketDataToken.objects.filter(pk=1, is_active=True).first()
    return token.access_token if token and token.is_valid() else None
