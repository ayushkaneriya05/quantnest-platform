# backend/ohlc/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import OHLC
from .serializers import OHLCSerializer

class OHLCListView(generics.ListAPIView):
    """
    Provides historical OHLC data for a given symbol and timeframe.
    """
    serializer_class = OHLCSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        symbol = self.request.query_params.get('symbol')
        tf = self.request.query_params.get('tf', '1m')
        limit = int(self.request.query_params.get('limit', 200))

        if not symbol:
            return OHLC.objects.none()

        # Ensure we fetch the most recent data
        return OHLC.objects.filter(
            symbol=symbol,
            tf=tf
        ).order_by('-ts')[:limit]