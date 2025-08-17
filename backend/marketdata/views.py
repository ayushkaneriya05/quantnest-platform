# backend/marketdata/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import status

from .storage import get_bootstrap_ohlc

class OHLCView(APIView):
    """
    GET /api/v1/market/ohlc/?symbol=RELIANCE&tf=1m&limit=500
    Returns list of { ts, o, h, l, c, v } ordered oldest->newest.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        tf = request.query_params.get("tf", "1m")
        try:
            limit = int(request.query_params.get("limit", "500"))
        except ValueError:
            limit = 500
        if not symbol:
            return Response({"detail": "symbol required"}, status=status.HTTP_400_BAD_REQUEST)
        data = get_bootstrap_ohlc(symbol, tf, limit)
        return Response(data)
