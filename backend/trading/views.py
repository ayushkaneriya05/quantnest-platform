from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Instrument, Watchlist
from .serializers import InstrumentSerializer, WatchlistSerializer

class InstrumentSearchView(generics.ListAPIView):
    """
    Provides a search endpoint for instruments based on symbol or company name.
    """
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('query', '')
        if query:
            # Case-insensitive search on both symbol and company name
            return Instrument.objects.filter(
                models.Q(symbol__icontains=query) | models.Q(company_name__icontains=query)
            )[:10] # Limit results to 10
        return Instrument.objects.none()

class WatchlistView(views.APIView):
    """
    API View for retrieving, adding to, and removing from a user's watchlist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        serializer = WatchlistSerializer(watchlist)
        return Response(serializer.data)

    def post(self, request):
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response({"error": "instrument_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instrument = Instrument.objects.get(id=instrument_id)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        watchlist.instruments.add(instrument)
        
        serializer = WatchlistSerializer(watchlist)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response({"error": "instrument_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        watchlist.instruments.remove(instrument_id)

        serializer = WatchlistSerializer(watchlist)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ... (keep InstrumentSearchView and WatchlistView)
from .models import Account, Position, Order, TradeHistory
from .serializers import AccountSerializer, PositionSerializer, OrderSerializer, TradeHistorySerializer

class AccountView(generics.RetrieveAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return account

class PositionView(generics.ListAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Position.objects.filter(account=account)

class OrderView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Order.objects.filter(account=account).order_by('-created_at')

    def get_serializer_context(self):
        return {'request': self.request}

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Order.objects.filter(account=account, status='OPEN')

    def perform_destroy(self, instance):
        # Instead of deleting, we mark as cancelled
        instance.status = 'CANCELLED'
        instance.save()