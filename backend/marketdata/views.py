import logging
from datetime import datetime

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .calendar_service import EventCalendarService
from .live_feed import LiveMarketDataRegistry
from .models import MarketEvent
from .services import ChartDataService, MarketDataService
from .quote_store import QuoteStore
from instruments.models import Instrument
from backend.middleware.api_responses import api_json_error

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
        return api_json_error("Instrument symbol is required", status_code=400)

    normalized = MarketDataService.normalize_symbol(symbol)
    quote = QuoteStore.get_latest(normalized)
    if not quote:
        quote = MarketDataService.get_live_quote(normalized)
    if not quote:
        quote = MarketDataService.latest_quote_from_storage(normalized)
    if not quote:
        return JsonResponse(_empty_quote_payload(normalized))
    return JsonResponse({**quote, "available": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_quote(request):
    symbol = request.query_params.get("instrument")
    if not symbol:
        return api_json_error("Instrument symbol is required", status_code=400)

    normalized = MarketDataService.normalize_symbol(symbol)
    LiveMarketDataRegistry.add_symbols([normalized])
    quote = QuoteStore.get_latest(normalized)
    if not quote:
        quote = MarketDataService.get_live_quote(normalized)
    if not quote:
        quote = MarketDataService.latest_quote_from_storage(normalized)
    if not quote:
        return api_json_error("Quote unavailable", status_code=404)
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
        quote = QuoteStore.get_latest(symbol)
        if not quote:
            quote = MarketDataService.get_live_quote(symbol)
        if not quote:
            quote = MarketDataService.latest_quote_from_storage(symbol)
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
@permission_classes([IsAuthenticated])
def ohlc_data(request):
    symbol = request.query_params.get("instrument")
    resolution = request.query_params.get("resolution", "1D")
    if not symbol:
        return api_json_error("Instrument symbol is required", status_code=400)

    try:
        candles_data = ChartDataService.list_candles(
            symbol=MarketDataService.normalize_symbol(symbol),
            resolution=resolution,
            limit=500,
        )
    except ValueError as exc:
        return api_json_error(str(exc), status_code=400)

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
            return api_json_error("instrument_id is invalid", status_code=400)
        symbol = instrument.sym_ticker or instrument.symbol

    if not symbol:
        return api_json_error("symbol is required", status_code=400)

    try:
        payload = ChartDataService.chart_window(
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
        return api_json_error(str(exc), status_code=400)
    except Exception as exc:
        logger.exception("Failed loading candles for %s %s: %s", symbol, resolution, exc)
        return api_json_error("Unable to load candles", status_code=500)

    return JsonResponse(payload)
