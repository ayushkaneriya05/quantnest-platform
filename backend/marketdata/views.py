import logging
from datetime import datetime, timedelta, timezone

import pytz
from decouple import config
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly

from .calendar_service import EventCalendarService
from .live_feed import LiveMarketDataRegistry
from .models import MarketDataToken, MarketEvent
from .services import HistoricalCandleService, MarketDataService
from .streaming import MarketDataStreamer
from .utils import refresh_fyers_token, _get_token_row, _get_today_eod
from instruments.models import Instrument

logger = logging.getLogger(__name__)


def _empty_quote_payload(symbol):
    return {
        "symbol": symbol,
        "price": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": 0,
        "change": None,
        "change_percent": None,
        "timestamp": None,
        "available": False,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_tick_data(request):
    symbol = request.query_params.get("instrument")
    if not symbol:
        return JsonResponse({"error": "Instrument symbol is required"}, status=400)

    normalized = MarketDataService.normalize_symbol(symbol)
    quote = (
        MarketDataStreamer.get_cached_quote(normalized)
        or MarketDataStreamer.poll_latest_candle_quote(normalized)
    )
    if not quote:
        return JsonResponse(_empty_quote_payload(normalized))
    return JsonResponse({**quote, "available": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_quote(request):
    symbol = request.query_params.get("instrument")
    if not symbol:
        return JsonResponse({"error": "Instrument symbol is required"}, status=400)

    normalized = MarketDataService.normalize_symbol(symbol)
    LiveMarketDataRegistry.add_symbols([normalized])
    quote = MarketDataStreamer.get_cached_quote(normalized) or MarketDataStreamer.poll_latest_candle_quote(normalized)
    if not quote:
        return JsonResponse({"error": "Quote unavailable"}, status=404)
    return JsonResponse(quote)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_indices(request):
    indices = {
        "NIFTY 50": "NSE:NIFTY50-INDEX",
        "BANK NIFTY": "NSE:NIFTYBANK-INDEX",
        "SENSEX": "BSE:SENSEX-INDEX",
    }
    payload = []
    for name, symbol in indices.items():
        quote = MarketDataStreamer.get_cached_quote(symbol) or MarketDataStreamer.poll_latest_candle_quote(symbol)
        if quote:
            payload.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "price": quote.get("price", 0),
                    "timestamp": quote.get("timestamp"),
                }
            )
    return JsonResponse(payload, safe=False)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def market_events(request):
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    if start and end:
        queryset = EventCalendarService.get_events(start, end)
    else:
        today = datetime.now().date()
        queryset = MarketEvent.objects.filter(event_date__gte=today).select_related("instrument")[:100]

    data = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat(),
            "event_time": event.event_time.isoformat() if event.event_time else None,
            "title": event.title,
            "description": event.description,
            "impact": event.impact,
            "source": event.source,
            "instrument": event.instrument.symbol if event.instrument else None,
        }
        for event in queryset
    ]
    return JsonResponse(data, safe=False)


@api_view(["GET"])
@permission_classes([AllowAny])
def ohlc_data(request):
    symbol = request.query_params.get("instrument")
    resolution = request.query_params.get("resolution", "1D")
    if not symbol:
        return JsonResponse({"error": "Instrument symbol is required"}, status=400)

    try:
        candles_data = HistoricalCandleService.list_candles(
            symbol=MarketDataService.normalize_symbol(symbol),
            resolution=resolution,
            limit=500,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    payload = [{**candle, "time": candle["time"] * 1000} for candle in candles_data]
    return JsonResponse(payload, safe=False)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def candles(request):
    instrument_id = request.query_params.get("instrument_id")
    symbol = request.query_params.get("symbol") or request.query_params.get("instrument")
    resolution = request.query_params.get("interval", "1m")
    limit = request.query_params.get("limit", 200)
    before = request.query_params.get("before")

    if instrument_id:
        instrument = Instrument.objects.filter(id=instrument_id).first()
        if not instrument:
            return JsonResponse({"detail": "instrument_id is invalid"}, status=400)
        symbol = instrument.sym_ticker or instrument.symbol

    if not symbol:
        return JsonResponse({"detail": "symbol is required"}, status=400)

    try:
        payload = HistoricalCandleService.chart_window(
            symbol=symbol,
            resolution=resolution,
            limit=limit,
            before=before,
        )
        logger.info(
            "Retrieved %d chart candles for %s (%s), fetched=%d",
            len(payload["candles"]),
            symbol,
            resolution,
            payload["source"]["fetched_count"],
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("Failed loading candles for %s %s: %s", symbol, resolution, exc)
        return JsonResponse({"detail": "Unable to load candles"}, status=500)

    return JsonResponse(payload)


try:
    from fyers_apiv3 import fyersModel
except Exception as exc:
    logger.exception("fyers_apiv3.accessToken import failed: %s", exc)
    fyersModel = None


@api_view(["GET"])
@permission_classes([AllowAny])
def fyers_login(request):
    if fyersModel is None:
        return JsonResponse({"error": "fyers_apiv3 not installed on server"}, status=500)

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
        grant_type="authorization_code",
    )
    return redirect(session.generate_authcode())


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def fyers_callback(request):
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
        grant_type="authorization_code",
    )

    try:
        session.set_token(auth_code)
        token_resp = session.generate_token()
    except Exception as exc:
        logger.exception("Error exchanging auth_code for token: %s", exc)
        return JsonResponse({"error": "token exchange failed", "detail": str(exc)}, status=500)

    access_token = token_resp.get("access_token") or token_resp.get("accessToken")
    refresh_token = token_resp.get("refresh_token") or token_resp.get("refreshToken")
    expires_in = token_resp.get("expires_in") or token_resp.get("expiresIn") or None

    token_row = _get_token_row()
    token_row.access_token = access_token
    token_row.refresh_token = refresh_token
    token_row.token_type = token_resp.get("token_type", token_row.token_type)
    token_row.expires_at = _get_today_eod()
    if expires_in:
        try:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            token_row.expires_at = None
    token_row.save()

    if request.headers.get("Accept", "").startswith("application/json") or request.GET.get("json"):
        return JsonResponse({"status": "ok", "token_saved": True})
    return redirect(config("FRONTEND_URL"))


@api_view(["GET"])
@permission_classes([IsAdminUser])
def fyers_token_status(request):
    token_row = _get_token_row()
    return JsonResponse(
        {
            "has_token": bool(token_row.access_token),
            "is_valid": token_row.is_valid(),
            "expires_at": token_row.expires_at,
            "updated_at": token_row.updated_at,
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def fyers_token_refresh(request):
    token_row = _get_token_row()
    if not token_row:
        return JsonResponse({"error": "No active token row"}, status=400)

    refreshed = refresh_fyers_token(token_row)
    if not refreshed:
        return JsonResponse({"error": "refresh_failed"}, status=500)
    return JsonResponse({"status": "ok", "expires_at": token_row.expires_at})
