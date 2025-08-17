# backend/marketdata/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import status
from ohlc.models import OHLC
from ohlc.serializers import OHLCCandleSerializer
from django.utils.dateparse import parse_datetime
import math

class OHLCView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        tf = request.query_params.get("tf", "1m")
        limit = int(request.query_params.get("limit", 500))
        if not symbol:
            return Response({"detail": "symbol required"}, status=status.HTTP_400_BAD_REQUEST)

        # normalize tf to stored format (we used e.g., "1m", "5m" etc)
        tf_key = tf
        qs = OHLC.objects.filter(symbol__iexact=symbol, tf__iexact=tf_key).order_by("-ts")[:limit]
        qs = qs.order_by("ts")  # chronological order
        data = OHLCCandleSerializer(qs, many=True).data
        return Response(data)
