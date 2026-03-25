"""
Views for the instruments app.
"""
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Instrument, WatchlistInstrument
from .serializers import InstrumentSerializer, WatchlistInstrumentSerializer


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
        exchange = request.query_params.get('exchange', None)
        instrument_type = request.query_params.get('type', None)
        segment = request.query_params.get('segment', None)
        underlying = request.query_params.get('underlying', None)
        
        qs = self.get_queryset()
        if query:
            qs = qs.filter(symbol__icontains=query) | qs.filter(name__icontains=query) | qs.filter(sym_ticker__icontains=query)
        if exchange:
            qs = qs.filter(exchange=exchange)
        if instrument_type:
            qs = qs.filter(instrument_type=instrument_type)
        if segment:
            qs = qs.filter(segment=segment)
        if underlying:
            qs = qs.filter(underlying_symbol=underlying)
        
        # Order options by expiry and strike if querying options
        if instrument_type == 'OPTION' and underlying:
            qs = qs.order_by('expiry_date', 'strike_price')
            serializer = self.get_serializer(qs[:500], many=True)
        else:
            serializer = self.get_serializer(qs[:50], many=True)
            
        return Response(serializer.data)


class WatchlistInstrumentViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy watchlists."""
    serializer_class = WatchlistInstrumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = WatchlistInstrument.objects.filter(
            strategy__user=self.request.user
        ).select_related('instrument')
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs
