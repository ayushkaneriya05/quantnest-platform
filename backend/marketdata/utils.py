# backend/marketdata/utils.py
"""
Helpers for FYERS API access:
 - get_active_fyers_access_token(): returns the active token (DB lookup or env fallback)
 - build_fyers_rest_client(): returns an instance of the official fyers_apiv3 REST wrapper (FyersModel)
"""

import os
from typing import Optional

# attempt to import fyers client model
try:
    from fyers_apiv3 import fyersModel  # type: ignore
except Exception:
    fyersModel = None

# If you have a Django model like MarketDataToken, adapt the import below.
# This function will try DB first, then environment variables as fallback.
def get_active_fyers_access_token() -> Optional[str]:
    try:
        # lazy import to avoid startup crash where Django isn't fully configured
        from marketdata.models import MarketDataToken  # adapt path if different
        # prefer DB entry flagged active
        token_obj = MarketDataToken.objects.filter(active=True).order_by("-updated_at").first()
        if token_obj and getattr(token_obj, "access_token", None):
            return token_obj.access_token
    except Exception:
        # ignore DB errors (e.g., not configured) and fallback to env
        pass

    # fallback to env vars
    return os.getenv("FYERS_ACCESS_TOKEN") or os.getenv("FYERS_TOKEN") or os.getenv("FYERS_ACCESS_KEY")

def build_fyers_rest_client(client_id: Optional[str] = None, token: Optional[str] = None):
    """
    Return a fyersModel.FyersModel instance for calling fyers.history(...) and other REST endpoints.
    Raises ImportError if fyers_apiv3 not installed.
    """
    if fyersModel is None:
        raise ImportError("fyers_apiv3 is not installed. pip install fyers-apiv3")

    token = token or get_active_fyers_access_token()
    client_id = client_id or os.getenv("FYERS_CLIENT_ID") or os.getenv("FYERS_APP_ID")
    # Depending on the fyers_apiv3 version, constructor might be FyersModel(client_id=..., token=...) or similar.
    try:
        # preferred constructor in many examples:
        return fyersModel.FyersModel(client_id=client_id, token=token)
    except Exception:
        # fallback common alternative
        try:
            return fyersModel.FyersModel(client_id=client_id, access_token=token)
        except Exception as e:
            raise RuntimeError("Unable to create FyersModel client: " + str(e))
