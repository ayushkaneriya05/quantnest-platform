from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Instrument, Watchlist, Account, Position, Order, TradeHistory
from .serializers import (
    InstrumentSerializer,
    WatchlistSerializer,
    AccountSerializer,
    PositionSerializer,
    OrderSerializer,
    TradeHistorySerializer,
)
# --- Instrument and Watchlist Views ---

class InstrumentSearchView(generics.ListAPIView):
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('query', '')
        if len(query) >= 2:
            return Instrument.objects.filter(
                Q(symbol__icontains=query) | Q(company_name__icontains=query)
            )[:10]
        return Instrument.objects.none()

class WatchlistView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        return Response(WatchlistSerializer(watchlist).data)

    def post(self, request):
        instrument_id = request.data.get('instrument_id')
        instrument = get_object_or_404(Instrument, id=instrument_id)
        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        watchlist.instruments.add(instrument)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)

    def delete(self, request):
        instrument_id = request.data.get('instrument_id')
        instrument = get_object_or_404(Instrument, id=instrument_id)
        watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
        watchlist.instruments.remove(instrument)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)

# --- Account, Position, and Order Views ---

class AccountView(generics.RetrieveAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Account.objects.get_or_create(user=self.request.user)[0]

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

    def perform_create(self, serializer):
        """
        Creates the order with an 'OPEN' status.
        The separate execution engine is responsible for processing it.
        """
        order = serializer.save()


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Order.objects.filter(account=account, status='OPEN')

    def perform_update(self, serializer):
        # This handles the modification of an existing OPEN order (e.g., changing price/qty)
        order = serializer.save()

    def perform_destroy(self, instance):
        # This handles the cancellation of an OPEN order
        instance.status = 'CANCELLED'
        instance.save()

class TradeHistoryView(generics.ListAPIView):
    serializer_class = TradeHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return TradeHistory.objects.filter(order__account=account).order_by('-timestamp')