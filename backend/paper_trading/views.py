"""
Views for the paper_trading app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import PaperAccount, PaperPosition, PaperOrder, PaperTrade
from .serializers import (
    PaperAccountSerializer, PaperPositionSerializer,
    PaperOrderSerializer, PaperTradeSerializer, PlaceOrderSerializer
)


class PaperAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for paper trading accounts."""
    serializer_class = PaperAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the active paper account."""
        account = self.get_queryset().filter(is_active=True).first()
        if account:
            return Response(self.get_serializer(account).data)
        return Response({})
    
    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """Reset account to initial balance."""
        account = self.get_object()
        account.reset()
        # Also close all positions and cancel pending orders
        account.positions.all().delete()
        account.orders.filter(status__in=['PENDING', 'PLACED']).update(status='CANCELLED')
        return Response({'success': True, 'message': 'Account reset'})
    
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
            'pending_orders': account.orders.filter(status__in=['PENDING', 'PLACED']).count(),
        })


class PaperPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper positions (read-only)."""
    serializer_class = PaperPositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperPosition.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a position at current market price."""
        position = self.get_object()
        # In real implementation, this would create an exit order
        # For now, we simulate immediate close
        
        exit_price = position.current_price
        pnl = (exit_price - position.avg_price) * position.quantity
        if position.side == 'SELL':
            pnl = -pnl
        
        # Create trade record
        PaperTrade.objects.create(
            account=position.account,
            strategy=position.strategy,
            instrument=position.instrument,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.avg_price,
            entry_time=position.opened_at,
            exit_price=exit_price,
            exit_time=timezone.now(),
            exit_reason='MANUAL_CLOSE',
            gross_pnl=pnl,
            net_pnl=pnl,
            pnl_pct=(pnl / (position.avg_price * position.quantity)) * 100,
        )
        
        # Update account
        position.account.realized_pnl += pnl
        position.account.current_balance += pnl
        position.account.margin_used -= position.margin_blocked
        position.account.margin_available += position.margin_blocked
        position.account.save()
        
        # Delete position
        position.delete()
        
        return Response({'success': True, 'pnl': float(pnl)})


class PaperOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for paper orders."""
    serializer_class = PaperOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaperOrder.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')
    
    @action(detail=False, methods=['post'])
    def place(self, request):
        """Place a new order."""
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Verify account ownership
        try:
            account = PaperAccount.objects.get(id=data['account'], user=request.user)
        except PaperAccount.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        
        # Create order
        order = PaperOrder.objects.create(
            account=account,
            instrument_id=data['instrument'],
            strategy_id=data.get('strategy'),
            order_type=data['order_type'],
            product_type=data.get('product_type', 'MIS'),
            side=data['side'],
            quantity=data['quantity'],
            price=data.get('price'),
            trigger_price=data.get('trigger_price'),
            order_tag=data.get('order_tag', ''),
            status='PLACED',
        )
        
        # For market orders, execute immediately (simulated)
        if data['order_type'] == 'MARKET':
            order.status = 'FILLED'
            order.filled_quantity = order.quantity
            order.avg_fill_price = order.price or 0  # Would get from market data
            order.executed_at = timezone.now()
            order.save()
            
            # Create or update position
            # This is simplified - real implementation would be more complex
        
        return Response(PaperOrderSerializer(order).data, status=201)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending order."""
        order = self.get_object()
        if order.status not in ['PENDING', 'PLACED']:
            return Response({'error': 'Order cannot be cancelled'}, status=400)
        
        order.status = 'CANCELLED'
        order.save()
        return Response({'success': True})


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
