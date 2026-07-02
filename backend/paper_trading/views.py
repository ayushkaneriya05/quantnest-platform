from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from strategies.models import Strategy
from .models import (
    PaperAccount, PaperPosition, PaperOrder, PaperTrade,
    Portfolio, CapitalAllocation, FundTransaction, ExposureSnapshot, DailyPerformance
)
from .serializers import (
    PaperAccountSerializer, PaperPositionSerializer,
    PaperOrderSerializer, PaperTradeSerializer,
    PortfolioSerializer, CapitalAllocationSerializer,
    FundTransactionSerializer, ExposureSnapshotSerializer,
    DailyPerformanceSerializer
)
from .services import PaperExecutionService, PortfolioService


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

    @action(detail=False, methods=['post'])
    def create_paper_account(self, request):
        """Create or return paper account for strategy allocation."""
        strategy_id = request.data.get('strategy_id')
        if not strategy_id:
            return Response({'error': 'strategy_id required'}, status=400)

        try:
            strategy = Strategy.objects.get(id=strategy_id, user=request.user)
        except Strategy.DoesNotExist:
            return Response({'error': 'Strategy not found'}, status=404)

        portfolio = PortfolioService.get_or_create_portfolio(request.user)
        try:
            paper_account = PortfolioService.ensure_paper_account_for_strategy(portfolio, strategy)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        serializer = PaperAccountSerializer(paper_account)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """Deposit funds into portfolio."""
        amount = request.data.get('amount', 0)
        if float(amount or 0) <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        transaction = PortfolioService.deposit(request.user, amount, request.data.get('notes', ''))
        return Response({'success': True, 'new_balance': transaction.balance_after})
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw funds from portfolio."""
        amount = request.data.get('amount', 0)
        if float(amount or 0) <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        try:
            transaction = PortfolioService.withdraw(request.user, amount, request.data.get('notes', ''))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)
        return Response({'success': True, 'new_balance': transaction.balance_after})

    @action(detail=False, methods=['get'])
    def performance(self, request):
        portfolio = PortfolioService.get_or_create_portfolio(request.user)
        data = DailyPerformance.objects.filter(portfolio=portfolio).order_by('date')
        return Response(DailyPerformanceSerializer(data, many=True).data)

    @action(detail=False, methods=['get'])
    def exposure_history(self, request):
        portfolio = PortfolioService.get_or_create_portfolio(request.user)
        data = ExposureSnapshot.objects.filter(portfolio=portfolio).order_by('-snapshot_time')[:200]
        return Response(ExposureSnapshotSerializer(data, many=True).data)


class CapitalAllocationViewSet(viewsets.ModelViewSet):
    """ViewSet for capital allocations."""
    serializer_class = CapitalAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CapitalAllocation.objects.filter(portfolio__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create allocation using service logic."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        portfolio = serializer.validated_data['portfolio']
        strategy = serializer.validated_data['strategy']
        alloc_type = serializer.validated_data['allocation_type']
        
        val = serializer.validated_data['allocated_amount'] if alloc_type == 'FIXED' else serializer.validated_data['allocated_percentage']
        
        try:
            allocation = PortfolioService.allocate_to_strategy(portfolio, strategy, val, alloc_type)
            return Response(self.get_serializer(allocation).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update allocation using service logic."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        portfolio = instance.portfolio
        strategy = instance.strategy
        alloc_type = serializer.validated_data.get('allocation_type', instance.allocation_type)
        
        if alloc_type == 'FIXED':
            val = serializer.validated_data.get('allocated_amount', instance.allocated_amount)
        else:
            val = serializer.validated_data.get('allocated_percentage', instance.allocated_percentage)
            
        try:
            allocation = PortfolioService.allocate_to_strategy(portfolio, strategy, val, alloc_type)
            return Response(self.get_serializer(allocation).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Delete allocation with paper account options."""
        allocation = self.get_object()
        paper_account = getattr(allocation, 'paper_account', None)
        
        if paper_account:
            can_delete_account, delete_reason = PortfolioService.can_delete_paper_account(paper_account)
            return Response({
                'status': 'has_paper_account',
                'paper_account': {
                    'id': paper_account.id,
                    'name': paper_account.name,
                    'current_balance': str(paper_account.current_balance),
                    'total_pnl': str(paper_account.total_pnl),
                    'unrealized_pnl': str(paper_account.unrealized_pnl),
                },
                'can_delete_paper_account': can_delete_account,
                'delete_reason': delete_reason,
                'message': 'Allocation has an associated paper account. Confirm deletion options.',
            }, status=status.HTTP_200_OK)
        
        PortfolioService.deallocate_from_strategy(allocation)
        return Response({'success': True, 'message': 'Allocation deleted'}, status=200)
    
    @action(detail=True, methods=['post'])
    def confirm_delete(self, request, pk=None):
        """Confirm allocation deletion with optional paper account deletion."""
        allocation = self.get_object()
        paper_account = getattr(allocation, 'paper_account', None)
        delete_paper_account = request.data.get('delete_paper_account', False)
        
        if paper_account and delete_paper_account:
            can_delete, reason = PortfolioService.can_delete_paper_account(paper_account)
            if not can_delete:
                return Response({'error': reason}, status=status.HTTP_400_BAD_REQUEST)
            paper_account.delete()
        
        PortfolioService.deallocate_from_strategy(allocation)
        return Response({'success': True, 'message': 'Allocation deleted'}, status=200)
    
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


class PaperAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for paper trading accounts."""
    serializer_class = PaperAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_active=True)

    def perform_update(self, serializer):
        serializer.save()
    
    def destroy(self, request, pk=None):
        """Delete paper account with validation."""
        account = self.get_object()
        
        # Check if can be deleted
        can_delete, message = PortfolioService.can_delete_paper_account(account)
        if not can_delete:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete the account
        account.delete()
        return Response({'success': True, 'message': 'Paper account deleted'}, status=200)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the active paper account."""
        account = self.get_queryset().filter(is_active=True).first()
        if account:
            return Response(self.get_serializer(account).data)
        return Response({})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        account = self.get_object()
        account.is_active = True
        account.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(account).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        account = self.get_object()
        account.is_active = False
        account.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(account).data)
    
    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """Reset account to initial balance."""
        account = self.get_object()
        account.reset()
        # Also close all positions (strategy-managed positions)
        account.positions.all().delete()
        return Response({'success': True, 'message': 'Account reset'})
    
    @action(detail=True, methods=['post'])
    def validate_delete(self, request, pk=None):
        """Check if account can be deleted (used for UI validation)."""
        account = self.get_object()
        can_delete, message = PortfolioService.can_delete_paper_account(account)
        return Response({
            'can_delete': can_delete,
            'reason': message,
        })
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get account summary with stats."""
        account = self.get_object()
        trades = account.trades.all()
        
        winning = trades.filter(net_pnl__gt=0).count()
        losing = trades.filter(net_pnl__lt=0).count()
        
        return Response({
            'account': self.get_serializer(account).data,
            'total_trades': trades.count(),
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': (winning / trades.count() * 100) if trades.count() > 0 else 0,
            'open_positions': account.positions.count(),
        })


class PaperPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper positions (read-only - strategy managed only)."""
    serializer_class = PaperPositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperPosition.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')


class PaperOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper orders (read-only - strategy execution only)."""
    serializer_class = PaperOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperOrder.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')


class PaperTradeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper trades (read-only)."""
    serializer_class = PaperTradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperTrade.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get trade analytics."""
        qs = self.get_queryset()
        
        total = qs.count()
        if total == 0:
            return Response({
                'total_trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
            })
        
        winning = qs.filter(net_pnl__gt=0)
        losing = qs.filter(net_pnl__lt=0)
        
        from django.db.models import Sum, Avg
        
        return Response({
            'total_trades': total,
            'winning_trades': winning.count(),
            'losing_trades': losing.count(),
            'win_rate': (winning.count() / total) * 100,
            'avg_pnl': float(qs.aggregate(avg=Avg('net_pnl'))['avg'] or 0),
            'total_pnl': float(qs.aggregate(total=Sum('net_pnl'))['total'] or 0),
            'avg_winner': float(winning.aggregate(avg=Avg('net_pnl'))['avg'] or 0),
            'avg_loser': float(losing.aggregate(avg=Avg('net_pnl'))['avg'] or 0),
        })
