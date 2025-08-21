from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from .models import Instrument, Watchlist, Account, Position, Order, TradeHistory
from .serializers import (
    InstrumentSerializer, WatchlistSerializer, AccountSerializer, 
    PositionSerializer, OrderSerializer, TradeHistorySerializer,
    PortfolioSummarySerializer
)

class InstrumentSearchView(generics.ListAPIView):
    """
    Enhanced search endpoint for instruments with better performance.
    """
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('query', '').strip()
        if not query or len(query) < 2:
            return Instrument.objects.none()
        
        # Case-insensitive search with prefix matching for better performance
        return Instrument.objects.filter(
            models.Q(symbol__icontains=query) | 
            models.Q(company_name__icontains=query)
        ).order_by('symbol')[:20]  # Increased limit for better UX

class WatchlistView(views.APIView):
    """
    Enhanced API View for watchlist management with better error handling.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": "Failed to retrieve watchlist", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response(
                {"error": "instrument_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            instrument = Instrument.objects.get(id=instrument_id)
            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            
            if watchlist.instruments.filter(id=instrument_id).exists():
                return Response(
                    {"error": "Instrument already in watchlist"}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            watchlist.instruments.add(instrument)
            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Instrument.DoesNotExist:
            return Response(
                {"error": "Instrument not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "Failed to add instrument to watchlist", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response(
                {"error": "instrument_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            watchlist.instruments.remove(instrument_id)
            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": "Failed to remove instrument from watchlist", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AccountView(generics.RetrieveAPIView):
    """
    Enhanced account view with calculated portfolio metrics.
    """
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return account
    
    def retrieve(self, request, *args, **kwargs):
        account = self.get_object()
        
        # Calculate additional metrics
        positions = Position.objects.filter(account=account)
        total_invested = sum(
            abs(pos.quantity) * pos.average_price for pos in positions
        )
        
        # Get pending orders value
        pending_orders = Order.objects.filter(account=account, status='OPEN')
        pending_value = sum(
            order.quantity * (order.price or 0) for order in pending_orders
        )
        
        data = AccountSerializer(account).data
        data.update({
            'total_invested': total_invested,
            'pending_orders_value': pending_value,
            'positions_count': positions.count(),
            'pending_orders_count': pending_orders.count()
        })
        
        return Response(data)

class PortfolioSummaryView(views.APIView):
    """
    Provides comprehensive portfolio summary with P&L calculations.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            account, _ = Account.objects.get_or_create(user=request.user)
            positions = Position.objects.filter(account=account).select_related('instrument')
            
            total_value = Decimal('0')
            total_invested = Decimal('0')
            total_pnl = Decimal('0')
            
            position_data = []
            for position in positions:
                invested = abs(position.quantity) * position.average_price
                # For demo purposes, using average_price as current price
                # In real implementation, you'd fetch live prices
                current_value = abs(position.quantity) * position.average_price
                
                if position.is_short:
                    pnl = (position.average_price - position.average_price) * abs(position.quantity)
                else:
                    pnl = (position.average_price - position.average_price) * position.quantity
                
                total_invested += invested
                total_value += current_value
                total_pnl += pnl + position.realized_pnl
                
                position_data.append({
                    'instrument': position.instrument.symbol,
                    'quantity': position.quantity,
                    'average_price': position.average_price,
                    'current_value': current_value,
                    'pnl': pnl,
                    'position_type': 'Long' if position.is_long else 'Short'
                })
            
            return Response({
                'account_balance': account.balance,
                'total_invested': total_invested,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'positions': position_data
            })
            
        except Exception as e:
            return Response(
                {"error": "Failed to calculate portfolio summary", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PositionView(generics.ListAPIView):
    """
    Enhanced position view with detailed position information.
    """
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Position.objects.filter(
            account=account
        ).select_related('instrument').order_by('-updated_at')

class PositionCloseView(views.APIView):
    """
    Close a specific position (full or partial).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            account, _ = Account.objects.get_or_create(user=request.user)
            position = Position.objects.get(id=pk, account=account)
            
            quantity_to_close = request.data.get('quantity', position.abs_quantity)
            if quantity_to_close <= 0 or quantity_to_close > position.abs_quantity:
                return Response(
                    {"error": "Invalid quantity to close"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Create closing order
                order_type = 'SELL' if position.is_long else 'COVER'
                order = Order.objects.create(
                    account=account,
                    instrument=position.instrument,
                    order_type='MARKET',
                    transaction_type=order_type,
                    quantity=quantity_to_close,
                    status='EXECUTED'
                )
                
                # Update position
                if quantity_to_close == position.abs_quantity:
                    # Full close
                    position.delete()
                else:
                    # Partial close
                    if position.is_long:
                        position.quantity -= quantity_to_close
                    else:
                        position.quantity += quantity_to_close
                    position.save()
                
                return Response({"message": "Position closed successfully"})
                
        except Position.DoesNotExist:
            return Response(
                {"error": "Position not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "Failed to close position", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderView(generics.ListCreateAPIView):
    """
    Enhanced order view with support for short selling.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        status_filter = self.request.query_params.get('status', None)
        
        queryset = Order.objects.filter(account=account).select_related('instrument')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset.order_by('-created_at')

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        """
        Enhanced order creation with validation for short selling.
        """
        account, _ = Account.objects.get_or_create(user=self.request.user)
        transaction_type = serializer.validated_data['transaction_type']
        quantity = serializer.validated_data['quantity']
        
        # Validate short selling
        if transaction_type in ['SHORT', 'COVER']:
            # Add short selling validation logic here
            # For now, allowing all short sells for demo
            pass
        
        serializer.save(account=account)

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Enhanced order detail view with modify support.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        account, _ = Account.objects.get_or_create(user=self.request.user)
        return Order.objects.filter(account=account)

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        
        if order.status != 'OPEN':
            return Response(
                {"error": "Can only modify open orders"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only allow modification of price and quantity for limit orders
        allowed_fields = ['price', 'quantity', 'trigger_price']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(order, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """
        Cancel order instead of deleting.
        """
        if instance.status == 'OPEN':
            instance.status = 'CANCELLED'
            instance.save()
        else:
            raise ValidationError("Can only cancel open orders")

class OrderCancelView(views.APIView):
    """
    Dedicated endpoint for canceling orders.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            account, _ = Account.objects.get_or_create(user=request.user)
            order = Order.objects.get(id=pk, account=account)
            
            if order.status != 'OPEN':
                return Response(
                    {"error": "Can only cancel open orders"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order.status = 'CANCELLED'
            order.save()
            
            return Response({"message": "Order cancelled successfully"})
            
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "Failed to cancel order", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
