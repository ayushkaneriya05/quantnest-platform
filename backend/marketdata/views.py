# backend/marketdata/views.py
import logging
from datetime import datetime, timedelta
from decouple import config
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny

from .utils import refresh_fyers_token

from .models import MarketDataToken

logger = logging.getLogger(__name__)

# backend/marketdata/views.py
from django.utils import timezone
from .mongo_client import get_candles_collection

# A dictionary to map resolution strings to MongoDB's date truncation units.
# This makes the code cleaner and easier to extend.
RESOLUTION_MAP = {
    '1m': {'unit': 'minute', 'binSize': 1},
    '5m': {'unit': 'minute', 'binSize': 5},
    '15m': {'unit': 'minute', 'binSize': 15},
    '1h': {'unit': 'hour', 'binSize': 1},
    '1D': {'unit': 'day', 'binSize': 1},
    '1W': {'unit': 'week', 'binSize': 1},
}
from bson import SON

@api_view(['GET'])
@permission_classes([AllowAny])
def ohlc_data(request):
    symbol = request.query_params.get('instrument')
    resolution = request.query_params.get('resolution', '1D')

    if not symbol:
        return JsonResponse({"error": "Instrument symbol is required"}, status=400)
    if resolution not in RESOLUTION_MAP:
        return JsonResponse({"error": "Invalid resolution"}, status=400)

    instrument_symbol = f"NSE:{symbol.upper()}-EQ"
    candles_collection = get_candles_collection()
    fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)

    if resolution == '1m':
        def fetch_candles():
            return list(candles_collection.find(
                {
                    "instrument": instrument_symbol,
                    "resolution": "1m",
                    "timestamp": {"$lte": fifteen_minutes_ago}
                },
                {"_id": 0, "instrument": 0, "resolution": 0}
            ).sort("timestamp", 1))

        candles = fetch_candles()
        for candle in candles:
            candle["time"] = int(candle.pop("timestamp").timestamp() * 1000)

    else:
        agg_params = RESOLUTION_MAP[resolution]
        unit_seconds = {
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
        }[agg_params["unit"]] * agg_params["binSize"]

        pipeline = [
            {"$match": {
                "instrument": instrument_symbol,
                "resolution": "1m",
                "timestamp": {"$lte": fifteen_minutes_ago}
            }},
            {"$sort": {"timestamp": 1}},
            {"$project": {
                "timestamp": 1,
                "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1,
                "epoch": {"$toLong": {"$divide": [{"$subtract": ["$timestamp", datetime(1970,1,1)]}, 1000]}}
            }},
            {"$group": {
                "_id": {"$multiply": [{"$floor": {"$divide": ["$epoch", unit_seconds]}}, unit_seconds]},
                "open": {"$first": "$open"},
                "high": {"$max": "$high"},
                "low": {"$min": "$low"},
                "close": {"$last": "$close"},
                "volume": {"$sum": "$volume"}
            }},
            {"$project": {
                "_id": 0,
                "time": {"$multiply": ["$_id", 1000]},
                "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1
            }},
            {"$sort": SON([("time", 1)])}
        ]

        def aggregate_candles():
            return list(candles_collection.aggregate(pipeline))

        candles = aggregate_candles()

    return JsonResponse(candles, safe=False)



try:
    from fyers_apiv3 import fyersModel
except Exception as exc:
    logger.exception("fyers_apiv3.accessToken import failed: %s", exc)
    fyersModel = None

def _get_or_create_token_row():
    obj, _ = MarketDataToken.objects.get_or_create(pk=1)
    return obj

@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def fyers_login(request):
    """
    Redirect the client to Fyers authorization URL.
    The generated URL will redirect to FYERS_REDIRECT_URI with ?auth_code=...
    """
    if fyersModel is None:
        return JsonResponse({"error": "fyers_apiv3 not installed on server"}, status=500)

    client_id = getattr(settings, "FYERS_CLIENT_ID", None)
    secret_key = getattr(settings, "FYERS_SECRET", None)
    redirect_uri = getattr(settings, "FYERS_REDIRECT_URI", None)
    if not client_id or not secret_key or not redirect_uri:
        return JsonResponse({"error": "FYERS_CLIENT_ID / FYERS_SECRET / FYERS_REDIRECT_URI not configured"}, status=500)

    # prepare session model for authcode generation
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    auth_url = session.generate_authcode()
    return redirect(auth_url)

from datetime import datetime, timedelta
import pytz

# Assume IST timezone
ist = pytz.timezone("Asia/Kolkata")

# Fyers tokens always expire at EOD IST
today_eod = datetime.now(ist).replace(hour=23, minute=59, second=59, microsecond=0)

@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
@csrf_exempt
def fyers_callback(request):
    """
    Endpoint that Fyers will redirect to with ?auth_code=...
    Exchanges auth_code for access_token and saves it to MarketDataToken (id=1).
    """
    if fyersModel is None:
        return JsonResponse({"error": "fyers_apiv3 not installed on server"}, status=500)

    auth_code = request.GET.get("auth_code") or request.GET.get("authCode")
    if not auth_code:
        return HttpResponseBadRequest("Missing auth_code in callback query params")

    client_id = getattr(settings, "FYERS_CLIENT_ID", None)
    secret_key = getattr(settings, "FYERS_SECRET", None)
    redirect_uri = getattr(settings, "FYERS_REDIRECT_URI", None)
    if not client_id or not secret_key or not redirect_uri:
        return JsonResponse({"error": "FYERS_CLIENT_ID / FYERS_SECRET / FYERS_REDIRECT_URI not configured"}, status=500)

    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    # Exchange
    try:
        session.set_token(auth_code)
        token_resp = session.generate_token()
    except Exception as exc:
        logger.exception("Error exchanging auth_code for token: %s", exc)
        return JsonResponse({"error": "token exchange failed", "detail": str(exc)}, status=500)

    # token_resp expected to contain keys: access_token, refresh_token, expires_in
    access_token = token_resp.get("access_token") or token_resp.get("accessToken")
    refresh_token = token_resp.get("refresh_token") or token_resp.get("refreshToken")
    expires_in = token_resp.get("expires_in") or token_resp.get("expiresIn") or None

    token_row = _get_or_create_token_row()
    token_row.access_token = access_token
    token_row.refresh_token = refresh_token
    token_row.token_type = token_resp.get("token_type", token_row.token_type)
    token_row.expires_at = today_eod
    if expires_in:
        try:
            expires_seconds = int(expires_in)
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        except Exception:
            token_row.expires_at = None
    token_row.save()

    # For convenience, redirect to a simple success page or return JSON.
    # If callback is called server-side (not via browser), return JSON.
    if request.headers.get("Accept", "").startswith("application/json") or request.GET.get("json"):
        return JsonResponse({"status": "ok", "token_saved": True})
    # else redirect to a simple page (update to your frontend URL if needed)
    return redirect(config("FRONTEND_URL"))

@api_view(["GET"])
@permission_classes([IsAdminUser])
def fyers_token_status(request):
    """
    Admin endpoint: show current token metadata
    """
    token_row = _get_or_create_token_row()
    data = {
        "has_token": bool(token_row.access_token),
        "is_valid": token_row.is_valid(),
        "expires_at": token_row.expires_at,
        "updated_at": token_row.updated_at,
    }
    return JsonResponse(data)

@api_view(["POST"])
@permission_classes([IsAdminUser])
def fyers_token_refresh(request):
    """API endpoint: manually refresh token"""
    token_row = MarketDataToken.objects.filter(is_active=True).first()
    if not token_row:
        return JsonResponse({"error": "No active token row"}, status=400)

    refreshed = refresh_fyers_token(token_row)
    if not refreshed:
        return JsonResponse({"error": "refresh_failed"}, status=500)

    return JsonResponse({"status": "ok", "expires_at": token_row.expires_at})