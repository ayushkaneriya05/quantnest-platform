"""
Views for the instruments app.
"""
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date
from .models import Instrument, WatchlistInstrument, ExecutionRoute
from .serializers import InstrumentSerializer, WatchlistInstrumentSerializer, ExecutionRouteSerializer


class InstrumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for browsing instruments (read-only)."""
    queryset = Instrument.objects.filter(is_active=True)
    serializer_class = InstrumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['symbol', 'name', 'sym_ticker']
    ordering_fields = ['symbol', 'lot_size']
    ordering = ['symbol']
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search instruments by query with optional filters."""
        query = request.query_params.get('q', '')
        equity_only = request.query_params.get('equity_only', 'false').lower() == 'true'
        exchange = request.query_params.get('exchange', None)
        instrument_type = request.query_params.get('type', None)
        segment = request.query_params.get('segment', None)
        underlying = request.query_params.get('underlying', None)
        has_futures = request.query_params.get('has_futures', 'false').lower() == 'true'
        has_options = request.query_params.get('has_options', 'false').lower() == 'true'
        
        qs = self.get_queryset()
        
        if equity_only:
            # Only NSE stocks/equities
            qs = qs.filter(exchange='NSE', segment=10, instrument_type='STOCK')

        if query:
            from django.db.models import Case, When, Value, IntegerField
            qs = qs.filter(symbol__icontains=query) | qs.filter(name__icontains=query) | qs.filter(sym_ticker__icontains=query)
            qs = qs.annotate(
                match_score=Case(
                    When(symbol__iexact=query, then=Value(1)),
                    When(symbol__istartswith=query, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField()
                )
            )
        if exchange and not equity_only: # Filter if provided and not already filtered by equity_only
            qs = qs.filter(exchange=exchange)
        if instrument_type and not equity_only:
            types = [t.strip() for t in instrument_type.split(',')]
            qs = qs.filter(instrument_type__in=types)
        if segment and not equity_only:
            qs = qs.filter(segment=segment)
        if underlying:
            qs = qs.filter(underlying_symbol=underlying)
        if has_futures:
            qs = qs.filter(has_futures=True)
        if has_options:
            qs = qs.filter(has_options=True)
        
        # Filter out expired contracts
        from django.db.models import Q
        qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=date.today()))
        # Order options by expiry and strike if querying options
        if instrument_type == 'OPTION' and underlying:
            qs = qs.order_by('expiry_date', 'strike_price')
            serializer = self.get_serializer(qs[:500], many=True)
        else:
            if query:
                qs = qs.order_by('match_score', 'symbol')
            serializer = self.get_serializer(qs[:50], many=True)
            
        return Response(serializer.data)


class WatchlistInstrumentViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy watchlists."""
    serializer_class = WatchlistInstrumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = WatchlistInstrument.objects.filter(
            strategy__user=self.request.user
        ).select_related('instrument').prefetch_related('execution_routes')
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs


class ExecutionRouteViewSet(viewsets.ModelViewSet):
    """ViewSet for execution route overrides on watchlist instruments."""
    serializer_class = ExecutionRouteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = ExecutionRoute.objects.filter(
            watchlist_instrument__strategy__user=self.request.user
        )
        wi_id = self.request.query_params.get('watchlist_instrument')
        if wi_id:
            qs = qs.filter(watchlist_instrument_id=wi_id)
        return qs

