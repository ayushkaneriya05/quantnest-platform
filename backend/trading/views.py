from common.enums import (
    Exchange, InstrumentType, TerminalOrderType, TerminalOrderStatus,
    TerminalPositionAction, Side, Timezone,
)
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Account, Position, Order, TradeHistory, ClosedPositionLog, Watchlist
from .serializers import (
    InstrumentSerializer,
    WatchlistSerializer,
    AccountSerializer,
    PositionSerializer,
    OrderSerializer,
    TradeHistorySerializer,
    ClosedPositionLogSerializer,
)
from .services import (
    TradingTerminalService,
    TradingAccountService,
    TradingInstrumentService,
    TradingOrderService,
    TradingWatchlistService,
)


def filter_history_dates(queryset, request, field):
    from datetime import date, datetime, time, timedelta
    from zoneinfo import ZoneInfo
    from rest_framework.exceptions import ValidationError
    try:
        start = date.fromisoformat(request.query_params['start_date']) if request.query_params.get('start_date') else None
        end = date.fromisoformat(request.query_params['end_date']) if request.query_params.get('end_date') else None
    except ValueError:
        raise ValidationError('Use YYYY-MM-DD for history dates.') from None
    if start and end and end < start:
        raise ValidationError('End date must not precede start date.')
    if start:
        queryset = queryset.filter(**{field + '__gte': datetime.combine(start, time.min, ZoneInfo(Timezone.ASIA_KOLKATA))})
    if end:
        queryset = queryset.filter(**{field + '__lt': datetime.combine(end + timedelta(days=1), time.min, ZoneInfo(Timezone.ASIA_KOLKATA))})
    return queryset

# --- Instrument and Watchlist Views ---

class InstrumentSearchView(generics.ListAPIView):
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from rest_framework import serializers
        class SearchInput(serializers.Serializer):
            q = serializers.CharField(default='', allow_blank=True, max_length=100)
            exchange = serializers.ChoiceField(choices=Exchange.choices, allow_blank=True, default='')
            instrument_type = serializers.ChoiceField(choices=InstrumentType.choices, allow_blank=True, default='')
            expiry_date = serializers.DateField(required=False)
        data = SearchInput(data=self.request.query_params)
        data.is_valid(raise_exception=True)
        fields = dict(data.validated_data)
        return TradingInstrumentService.search(fields.pop('q'), **fields)

class WatchlistView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import serializers
        identity = serializers.IntegerField(min_value=0).run_validation(request.query_params.get('watchlist_id', 0))
        watchlist = TradingWatchlistService.get_watchlist(request.user, identity)
        return Response(WatchlistSerializer(watchlist).data)

    def post(self, request):
        from rest_framework import serializers
        sym_ticker = serializers.CharField(max_length=100).run_validation(request.data.get('sym_ticker'))
        identity = serializers.IntegerField(min_value=0).run_validation(request.query_params.get('watchlist_id', 0))
        watchlist = TradingWatchlistService.add_instrument(request.user, sym_ticker, identity)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)

    def delete(self, request):
        from rest_framework import serializers
        sym_ticker = serializers.CharField(max_length=100).run_validation(request.data.get('sym_ticker'))
        identity = serializers.IntegerField(min_value=0).run_validation(request.query_params.get('watchlist_id', 0))
        watchlist = TradingWatchlistService.remove_instrument(request.user, sym_ticker, identity)
        return Response(WatchlistSerializer(watchlist).data, status=status.HTTP_200_OK)


class WatchlistCollectionView(generics.ListCreateAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).prefetch_related('instruments').order_by('id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    from .models import Watchlist
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.Watchlist.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        if self.get_queryset().count() <= 1:
            raise ValidationError('Keep at least one watchlist.')
        instance.delete()

# --- Account, Position, and Order Views ---

class AccountView(generics.RetrieveUpdateAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return TradingAccountService.get_or_create_account(self.request.user)


class PositionView(generics.ListAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Position.objects.filter(account=account).select_related('instrument').order_by('id')

class PositionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Position.objects.filter(account=account).select_related('instrument')


class PositionActionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        from django.db import transaction
        from django.shortcuts import get_object_or_404
        from rest_framework import serializers

        class ActionInput(serializers.Serializer):
            action = serializers.ChoiceField(choices=TerminalPositionAction.choices)
            quantity = serializers.IntegerField(min_value=1, required=False)
            settlement_price = serializers.DecimalField(max_digits=20, decimal_places=8, min_value=0, required=False)

        data = ActionInput(data=request.data)
        data.is_valid(raise_exception=True)
        action = data.validated_data['action']
        with transaction.atomic():
            account = TradingAccountService.get_or_create_account(request.user)
            Account.objects.select_for_update().get(pk=account.pk)
            position = get_object_or_404(Position.objects.select_for_update().select_related('instrument'), pk=id, account=account)
            quantity = abs(position.quantity) if action in (TerminalPositionAction.CLOSE, TerminalPositionAction.SETTLE) else data.validated_data.get('quantity')
            if not quantity:
                raise serializers.ValidationError('Quantity is required.')
            if action == TerminalPositionAction.REDUCE and quantity > abs(position.quantity):
                raise serializers.ValidationError('Reduction exceeds the current position.')
            same_side = Side.BUY if position.quantity > 0 else Side.SELL
            side = same_side if action == TerminalPositionAction.INCREASE else (Side.SELL if same_side == Side.BUY else Side.BUY)
            if action == TerminalPositionAction.REVERSE:
                quantity += abs(position.quantity)
            if action == TerminalPositionAction.SETTLE:
                from common.costs import snapshot_charge_profile
                if 'settlement_price' not in data.validated_data:
                    raise serializers.ValidationError('Enter the official settlement price for this simulation.')
                from uuid import uuid4
                from common.enums import ExecutionMode, ExecutionCommandType
                from execution.repository import enqueue
                from marketdata.calendar import MarketSessionCalendar
                calendar = MarketSessionCalendar.for_instrument(position.instrument)
                if position.instrument.expiry_date:
                    calendar.load_holidays(position.instrument.expiry_date, position.instrument.expiry_date)
                if not position.instrument.expiry_date or timezone.now() < calendar.session_close(position.instrument.expiry_date):
                    raise serializers.ValidationError('Settlement is available only after contract expiry.')
                order = Order.objects.create(account=account, instrument=position.instrument, request_id=uuid4(),
                    transaction_type=side, quantity=quantity, order_type=TerminalOrderType.SETTLEMENT, reduce_only=True,
                    charge_profile_snapshot=snapshot_charge_profile(account.charge_profile))
                enqueue(ExecutionMode.TERMINAL, account.pk, ExecutionCommandType.SETTLE,
                    {'instrument_id': position.instrument_id, 'settlement_price': str(data.validated_data['settlement_price'])},
                    request_id=order.request_id)
            else:
                order = TradingOrderService.create_order(request.user, {'instrument': position.instrument,
                    'transaction_type': side, 'quantity': quantity, 'order_type': TerminalOrderType.MARKET,
                    'reduce_only': action in (TerminalPositionAction.CLOSE, TerminalPositionAction.REDUCE)})
        return Response(OrderSerializer(order).data)


class CancelOrdersView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework import serializers

        class CancelInput(serializers.Serializer):
            ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)

        data = CancelInput(data=request.data)
        data.is_valid(raise_exception=True)
        orders = Order.objects.filter(account__user=request.user, pk__in=data.validated_data['ids'], status=TerminalOrderStatus.OPEN)
        count = 0
        for order in orders:
            TradingOrderService.cancel_order(order)
            count += 1
        return Response({'cancelled': count})


class OrderPreviewView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from decimal import Decimal
        from marketdata.quotes import read_quote
        from execution.preparation import contract_from_instrument
        serializer = OrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        instrument = data.pop('instrument')
        account = TradingAccountService.get_or_create_account(request.user)
        quote = read_quote(instrument.sym_ticker)
        price = data.get('price') or data.get('trigger_price')
        if price is None and quote['available']:
            price = Decimal(str(quote['price']))
        if price is None:
            return Response({'available': False, 'reason': 'Waiting for a price observation.'})
        order = Order(account=account, instrument=instrument, **data)
        contract = contract_from_instrument(instrument)
        try:
            contract.validate(order.quantity,
                (order.price, order.trigger_price, order.stop_loss, order.take_profit), timezone.now())
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc)) from None
        value = contract.value(price, order.quantity)
        return Response({'available': True, 'notional': str(value),
                         'estimated_funds': str(TradingOrderService.required_cash(order, account, price)),
                         'margin_basis': 'Configured simulation margin; not a broker margin quotation.'})

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
            queryset = queryset.filter(Q(instrument__sym_ticker__icontains=symbol_filter) | Q(instrument__symbol__icontains=symbol_filter))
            
        return filter_history_dates(queryset, self.request, 'created_at')

    def get_serializer_context(self):
        return {'request': self.request}

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        return Order.objects.filter(account=account, status=TerminalOrderStatus.OPEN).select_related('instrument')

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
            queryset = queryset.filter(Q(order__instrument__sym_ticker__icontains=symbol_filter) | Q(order__instrument__symbol__icontains=symbol_filter))
        
        if side_filter:
            queryset = queryset.filter(order__transaction_type__iexact=side_filter)
            
        return filter_history_dates(queryset, self.request, 'timestamp')

class ClosedPositionLogView(generics.ListAPIView):
    serializer_class = ClosedPositionLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricalDataPagination

    def get_queryset(self):
        account = TradingAccountService.get_or_create_account(self.request.user)
        queryset = ClosedPositionLog.objects.filter(account=account).select_related('instrument').order_by('-exit_time')
        
        symbol_filter = self.request.query_params.get('symbol')
        if symbol_filter:
            queryset = queryset.filter(Q(instrument__sym_ticker__icontains=symbol_filter) | Q(instrument__symbol__icontains=symbol_filter))
            
        return filter_history_dates(queryset, self.request, 'exit_time')

class TerminalSnapshotView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework import serializers
        identity = serializers.IntegerField(min_value=0).run_validation(request.query_params.get('watchlist_id', 0))
        return Response(TradingTerminalService.build_snapshot(request.user, identity))


class TerminalStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        from common.redis import runtime_redis
        redis = runtime_redis()
        return Response({'execution_running': int(redis.get('quantnest:execution:workers') or 0) == settings.EXECUTION_WORKERS,
            'market_data': bool(redis.exists('quantnest:lease:market-data'))})
