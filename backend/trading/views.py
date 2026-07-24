from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Account, Position, Order, TradeHistory, ClosedPositionLog
from .serializers import (
    InstrumentSerializer,
    WatchlistSerializer,
    AccountSerializer,
    PositionSerializer,
    OrderSerializer,
    TradeHistorySerializer,
    AccountSummarySerializer,
    ClosedPositionLogSerializer,
)
from .services import (
    PaperTradingTerminalService,
    TradingAccountService,
    TradingInstrumentService,
    TradingOrderService,
    TradingWatchlistService,
)

# --- Instrument and Watchlist Views ---

class InstrumentSearchView(generics.ListAPIView):
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', self.request.query_params.get('query', ''))
        equity_only = self.request.query_params.get('equity_only', 'false').lower() == 'true'
        return TradingInstrumentService.search(query, equity_only=equity_only)

class WatchlistView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        watchlist = TradingWatchlistService.get_watchlist(request.user)
        return Response(WatchlistSerializer(watchlist).data)

    def post(self, request):
        instrument_id = request.data.get('instrument_id')
        watchlist = TradingWatchlistService.add_instrument(request.user, instrument_id)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)

    def delete(self, request):
        instrument_id = request.data.get('instrument_id')
        watchlist = TradingWatchlistService.remove_instrument(request.user, instrument_id)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)

# --- Account, Position, and Order Views ---

class AccountView(generics.RetrieveAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return TradingAccountService.get_or_create_account(self.request.user)

class PositionView(generics.ListAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Position.objects.filter(account=account)

class PositionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Position.objects.filter(account=account)
        
    def perform_update(self, serializer):
        position = serializer.save()
        TradingOrderService.sync_position_sl_tp_orders(position)

class HistoricalDataPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class OrderView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricalDataPagination

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        queryset = Order.objects.filter(account=account).select_related('instrument').order_by('-created_at')
        
        status_filter = self.request.query_params.get('status')
        symbol_filter = self.request.query_params.get('symbol')
        
        if status_filter:
            queryset = queryset.filter(status__iexact=status_filter)
        if symbol_filter:
            queryset = queryset.filter(instrument__symbol__icontains=symbol_filter)
            
        return queryset

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        order = serializer.save()

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Order.objects.filter(account=account, status='OPEN')

    def perform_update(self, serializer):
        order = serializer.save()
        TradingOrderService.sync_order_to_position(order)

    def perform_destroy(self, instance):
        TradingOrderService.cancel_order(instance)

class TradeHistoryView(generics.ListAPIView):
    serializer_class = TradeHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricalDataPagination

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        queryset = TradeHistory.objects.filter(order__account=account).select_related('order', 'order__instrument').order_by('-timestamp')
        
        symbol_filter = self.request.query_params.get('symbol')
        side_filter = self.request.query_params.get('side') # BUY/SELL
        
        if symbol_filter:
            queryset = queryset.filter(order__instrument__symbol__icontains=symbol_filter)
        if side_filter:
            queryset = queryset.filter(order__transaction_type__iexact=side_filter)
            
        return queryset

class ClosedPositionLogView(generics.ListAPIView):
    serializer_class = ClosedPositionLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricalDataPagination

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        queryset = ClosedPositionLog.objects.filter(account=account).select_related('instrument').order_by('-exit_time')
        
        symbol_filter = self.request.query_params.get('symbol')
        if symbol_filter:
            queryset = queryset.filter(instrument__symbol__icontains=symbol_filter)
            
        return queryset

class AccountSummaryView(generics.RetrieveAPIView):
    """
    Provides a consolidated summary of the user's trading account,
    including current balance, P&L, positions, and complete trade history.
    """
    serializer_class = AccountSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        account, _ = Account.objects.prefetch_related(
            'positions__instrument'
        ).get_or_create(user=self.request.user)
        return account


class TerminalSnapshotView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PaperTradingTerminalService.build_snapshot(request.user))
