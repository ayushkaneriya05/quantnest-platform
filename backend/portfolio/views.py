"""
Views for the portfolio app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import (
    Portfolio, CapitalAllocation, FundTransaction,
    ExposureSnapshot, DailyPerformance
)
from .serializers import (
    PortfolioSerializer, CapitalAllocationSerializer,
    FundTransactionSerializer, ExposureSnapshotSerializer,
    DailyPerformanceSerializer
)


class PortfolioViewSet(viewsets.ModelViewSet):
    """ViewSet for user portfolio."""
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's portfolio (creates if not exists)."""
        portfolio, created = Portfolio.objects.get_or_create(
            user=request.user,
            defaults={'name': 'Primary Portfolio'}
        )
        serializer = self.get_serializer(portfolio)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """Deposit funds into portfolio."""
        portfolio = self.get_object()
        amount = request.data.get('amount', 0)
        
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        
        balance_before = portfolio.current_capital
        portfolio.current_capital += amount
        portfolio.save()
        
        FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type='DEPOSIT',
            amount=amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=request.data.get('notes', '')
        )
        
        return Response({'success': True, 'new_balance': portfolio.current_capital})
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw funds from portfolio."""
        portfolio = self.get_object()
        amount = request.data.get('amount', 0)
        
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        if amount > portfolio.current_capital:
            return Response({'error': 'Insufficient funds'}, status=400)
        
        balance_before = portfolio.current_capital
        portfolio.current_capital -= amount
        portfolio.save()
        
        FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type='WITHDRAWAL',
            amount=-amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=request.data.get('notes', '')
        )
        
        return Response({'success': True, 'new_balance': portfolio.current_capital})


class CapitalAllocationViewSet(viewsets.ModelViewSet):
    """ViewSet for capital allocations."""
    serializer_class = CapitalAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CapitalAllocation.objects.filter(portfolio__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_strategy(self, request):
        """Get allocation for a specific strategy."""
        strategy_id = request.query_params.get('strategy_id')
        if not strategy_id:
            return Response({'error': 'strategy_id required'}, status=400)
        
        try:
            allocation = self.get_queryset().get(strategy_id=strategy_id)
            return Response(self.get_serializer(allocation).data)
        except CapitalAllocation.DoesNotExist:
            return Response({}, status=404)


class FundTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for fund transactions (read-only)."""
    serializer_class = FundTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FundTransaction.objects.filter(portfolio__user=self.request.user)


class ExposureSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for exposure snapshots."""
    serializer_class = ExposureSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ExposureSnapshot.objects.filter(portfolio__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest exposure snapshot."""
        snapshot = self.get_queryset().first()
        if snapshot:
            return Response(self.get_serializer(snapshot).data)
        return Response({})


class DailyPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for daily performance records."""
    serializer_class = DailyPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return DailyPerformance.objects.filter(portfolio__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def range(self, request):
        """Get performance for a date range."""
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        
        queryset = self.get_queryset()
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return Response(self.get_serializer(queryset, many=True).data)
