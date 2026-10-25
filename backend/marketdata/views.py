import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from .contracts import normalize_symbol
from .quotes import read_quote, refresh_quote, refresh_quotes
from .charts import ChartDataService
from instruments.models import Instrument
from backend.middleware.api_responses import api_json_error

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quote_snapshots(request):
    symbols = serializers.ListField(
        child=serializers.CharField(max_length=128), allow_empty=False, max_length=1000,
    ).run_validation(request.data.get("symbols"))
    try:
        return JsonResponse(refresh_quotes(symbols))
    except ValueError as exc:
        raise serializers.ValidationError(str(exc)) from exc


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_tick_data(request):
    symbol = request.query_params.get("instrument")
    if not symbol:
        return api_json_error("Instrument symbol is required", status_code=400)

    try:
        normalized = normalize_symbol(symbol)
        quote = read_quote(normalized)
        if quote['source'] in ('history', 'unavailable'):
            quote = refresh_quote(normalized)
    except (ValueError, Instrument.DoesNotExist) as exc:
        return api_json_error(str(exc), status_code=400)
    return JsonResponse(quote)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def candles(request):
    symbol = request.query_params.get("symbol") or request.query_params.get("instrument")
    resolution = request.query_params.get("interval", "1m")
    limit = request.query_params.get("limit", 200)
    before = request.query_params.get("before")

    if not symbol:
        return api_json_error("symbol is required", status_code=400)

    fetch_missing = serializers.BooleanField().run_validation(request.query_params.get('fetch_missing', False))
    try:
        payload = ChartDataService.chart_window(
            symbol=symbol,
            resolution=resolution,
            limit=limit,
            before=before,
            fetch_missing=fetch_missing,
        )
        logger.info(
            "Retrieved %d chart candles for %s (%s), fetched=%d",
            len(payload["candles"]),
            symbol,
            resolution,
            payload["source"]["fetched_count"],
        )
    except (ValueError, Instrument.DoesNotExist) as exc:
        return api_json_error(str(exc), status_code=400)
    except Exception as exc:
        logger.exception("Failed loading candles for %s %s: %s", symbol, resolution, exc)
        return api_json_error("Unable to load candles", status_code=500)

    return JsonResponse(payload)
