# backend/marketdata/views.py
import os
import logging
import json
from datetime import datetime, timedelta, timezone
from decouple import config

from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response

from .models import MarketDataToken
from ohlc.backfill import fetch_historical

logger = logging.getLogger(__name__)

try:
    from fyers_apiv3 import fyersModel
except Exception as exc:
    logger.exception("fyers_apiv3.accessToken import failed: %s", exc)
    fyersModel = None

def _get_or_create_token_row():
    obj, _ = MarketDataToken.objects.get_or_create(pk=1)
    return obj

@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_backfill(request):
    """
    POST payload: {"symbol":"NSE:SBIN-EQ", "from":"2025-07-01", "to":"2025-07-31", "res_minutes":15}
    Triggers a historical fetch via FYERS and returns count of candles stored.
    """
    body = request.data
    symbol = body.get("symbol")
    if not symbol:
        return Response({"error": "symbol required"}, status=400)
    from_s = body.get("from")
    to_s = body.get("to")
    res_minutes = int(body.get("res_minutes", 1))
    try:
        from_date = datetime.strptime(from_s, "%Y-%m-%d").date() if from_s else date.today() - timedelta(days=7)
        to_date = datetime.strptime(to_s, "%Y-%m-%d").date() if to_s else date.today()
    except Exception:
        return Response({"error": "invalid date format, use YYYY-MM-DD"}, status=400)

    candles = fetch_historical(symbol, from_date, to_date, resolution_minutes=res_minutes, save_to_db=True)
    return Response({"symbol": symbol, "candles_fetched": len(candles)})

@api_view(["GET"])
@permission_classes([AllowAny])
def symbol_search(request):
    """
    Searches for symbols from the nifty500_symbols.json file.
    """
    query = request.query_params.get('q', '').upper()
    if not query:
        return Response([], status=200)

    try:
        symbols_file_path = 'backend/data/nifty500_symbols.json'
        with open(symbols_file_path, 'r') as f:
            all_symbols = json.load(f)
        
        suggestions = [s for s in all_symbols if s.startswith(query)][:10] # Limit to 10 suggestions
        return Response(suggestions)
    except FileNotFoundError:
        return Response({"error": "Symbols file not found."}, status=500)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


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
    return redirect(config("FRONTEND_URL")+ "/login/")

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
    """
    Manually refresh the stored token using refresh_token.
    """
    if fyersModel is None:
        return JsonResponse({"error": "fyers_apiv3 not installed on server"}, status=500)

    token_row = _get_or_create_token_row()
    if not token_row.refresh_token:
        return JsonResponse({"error": "No refresh_token available"}, status=400)

    client_id = getattr(settings, "FYERS_CLIENT_ID", None)
    secret_key = getattr(settings, "FYERS_SECRET", None)
    redirect_uri = getattr(settings, "FYERS_REDIRECT_URI", None)
    if not client_id or not secret_key or not redirect_uri:
        return JsonResponse({"error": "FYERS_CLIENT_ID / FYERS_SECRET / FYERS_REDIRECT_URI not configured"}, status=500)

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
        return JsonResponse({"error": "refresh_failed", "detail": str(exc)}, status=500)

    token_row.access_token = resp.get("access_token") or resp.get("accessToken")
    token_row.refresh_token = resp.get("refresh_token") or resp.get("refreshToken")
    expires_in = resp.get("expires_in") or resp.get("expiresIn") or None
    if expires_in:
        try:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            token_row.expires_at = None
    token_row.save()
    return JsonResponse({"status": "ok", "expires_at": token_row.expires_at})