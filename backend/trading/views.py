from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

from .models import Instrument, Watchlist, Account, Position, Order, TradeHistory
from .serializers import (
    InstrumentSerializer, WatchlistSerializer, AccountSerializer, 
    PositionSerializer, OrderSerializer, TradeHistorySerializer
)

# Configure logging
logger = logging.getLogger(__name__)

class InstrumentSearchView(generics.ListAPIView):
    """
    Provides a search endpoint for instruments based on symbol or company name.
    Enhanced with better error handling and pagination.
    """
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            query = self.request.query_params.get('query', '').strip()
            if not query:
                return Instrument.objects.none()
            
            if len(query) < 2:
                return Instrument.objects.none()
            
            # Case-insensitive search on both symbol and company name
            return Instrument.objects.filter(
                models.Q(symbol__icontains=query) | models.Q(company_name__icontains=query)
            ).order_by('symbol')[:20]  # Limit results to 20 for performance
            
        except Exception as e:
            logger.error(f"Error in instrument search: {str(e)}")
            return Instrument.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in instrument search list: {str(e)}")
            return Response(
                {"error": "Failed to search instruments. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class WatchlistView(views.APIView):
    """
    API View for retrieving, adding to, and removing from a user's watchlist.
    Enhanced with better error handling and duplicate prevention.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving watchlist for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Failed to retrieve watchlist. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            instrument_id = request.data.get('instrument_id')
            if not instrument_id:
                return Response(
                    {"error": "instrument_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                instrument = Instrument.objects.get(id=instrument_id)
            except Instrument.DoesNotExist:
                return Response(
                    {"error": "Instrument not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            
            # Check if instrument already in watchlist
            if watchlist.instruments.filter(id=instrument_id).exists():
                return Response(
                    {"error": f"{instrument.symbol} is already in your watchlist"}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            watchlist.instruments.add(instrument)
            
            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error adding to watchlist for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Failed to add instrument to watchlist. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        try:
            instrument_id = request.data.get('instrument_id')
            if not instrument_id:
                return Response(
                    {"error": "instrument_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            watchlist, _ = Watchlist.objects.get_or_create(user=request.user)
            
            try:
                instrument = Instrument.objects.get(id=instrument_id)
                watchlist.instruments.remove(instrument)
            except Instrument.DoesNotExist:
                return Response(
                    {"error": "Instrument not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = WatchlistSerializer(watchlist)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error removing from watchlist for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Failed to remove instrument from watchlist. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AccountView(generics.RetrieveAPIView):
    """
    Enhanced account view with comprehensive portfolio calculations.
    """
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            account, created = Account.objects.get_or_create(
                user=self.request.user,
                defaults={'balance': Decimal('1000000.00')}  # 10 Lakhs default
            )
            return account
        except Exception as e:
            logger.error(f"Error retrieving account for user {self.request.user.id}: {str(e)}")
            raise

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in account retrieve: {str(e)}")
            return Response(
                {"error": "Failed to retrieve account details. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PositionView(generics.ListAPIView):
    """
    Enhanced position view with real-time P&L calculations.
    """
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            account, _ = Account.objects.get_or_create(user=self.request.user)
            return Position.objects.filter(account=account).select_related('instrument')
        except Exception as e:
            logger.error(f"Error retrieving positions for user {self.request.user.id}: {str(e)}")
            return Position.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in positions list: {str(e)}")
            return Response(
                {"error": "Failed to retrieve positions. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderView(generics.ListCreateAPIView):
    """
    Enhanced order view with comprehensive validation and short selling support.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            account, _ = Account.objects.get_or_create(user=self.request.user)
            return Order.objects.filter(account=account).select_related('instrument').order_by('-created_at')
        except Exception as e:
            logger.error(f"Error retrieving orders for user {self.request.user.id}: {str(e)}")
            return Order.objects.none()

    def get_serializer_context(self):
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating order for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Failed to place order. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Enhanced order detail view for modification and cancellation.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            account, _ = Account.objects.get_or_create(user=self.request.user)
            return Order.objects.filter(account=account).select_related('instrument')
        except Exception as e:
            logger.error(f"Error retrieving order queryset for user {self.request.user.id}: {str(e)}")
            return Order.objects.none()

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Only allow modification of open orders
            if instance.status != 'OPEN':
                return Response(
                    {"error": "Only open orders can be modified"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error updating order {kwargs.get('pk')} for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Failed to modify order. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        try:
            # Only allow cancellation of open orders
            if instance.status != 'OPEN':
                raise ValidationError("Only open orders can be cancelled")
            
            # Mark as cancelled instead of deleting
            instance.status = 'CANCELLED'
            instance.save()
        except Exception as e:
            logger.error(f"Error cancelling order {instance.id}: {str(e)}")
            raise

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in order destroy: {str(e)}")
            return Response(
                {"error": "Failed to cancel order. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TradeHistoryView(generics.ListAPIView):
    """
    View for retrieving user's trade history.
    """
    serializer_class = TradeHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            account, _ = Account.objects.get_or_create(user=self.request.user)
            return TradeHistory.objects.filter(
                order__account=account
            ).select_related('order', 'order__instrument').order_by('-timestamp')
        except Exception as e:
            logger.error(f"Error retrieving trade history for user {self.request.user.id}: {str(e)}")
            return TradeHistory.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in trade history list: {str(e)}")
            return Response(
                {"error": "Failed to retrieve trade history. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_position(request, position_id):
    """
    API endpoint to close a specific position by creating a market order.
    """
    try:
        account, _ = Account.objects.get_or_create(user=request.user)
        
        try:
            position = Position.objects.get(id=position_id, account=account)
        except Position.DoesNotExist:
            return Response(
                {"error": "Position not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Determine order parameters to close position
        transaction_type = 'SELL' if position.quantity > 0 else 'BUY'
        quantity = abs(position.quantity)
        
        # Create market order to close position
        order_data = {
            'instrument_id': position.instrument.id,
            'order_type': 'MARKET',
            'transaction_type': transaction_type,
            'quantity': quantity
        }
        
        serializer = OrderSerializer(data=order_data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response(
                {
                    "message": "Position close order placed successfully",
                    "order": OrderSerializer(order).data
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {"error": "Failed to create close order", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error closing position {position_id} for user {request.user.id}: {str(e)}")
        return Response(
            {"error": "Failed to close position. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def portfolio_summary(request):
    """
    API endpoint to get comprehensive portfolio summary.
    """
    try:
        account, _ = Account.objects.get_or_create(user=request.user)
        positions = Position.objects.filter(account=account).select_related('instrument')
        orders = Order.objects.filter(account=account, status='OPEN').select_related('instrument')
        
        # Calculate portfolio metrics
        total_investment = sum(
            abs(pos.quantity) * pos.average_price for pos in positions
        )
        
        total_current_value = 0
        total_pnl = 0
        
        for position in positions:
            # Mock current price calculation
            current_price = position.average_price * (1 + 0.02)  # Mock 2% change
            current_value = abs(position.quantity) * current_price
            pnl = (current_price - position.average_price) * position.quantity
            
            total_current_value += current_value
            total_pnl += pnl
        
        # Calculate returns
        return_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        summary = {
            'account_balance': account.balance,
            'total_investment': total_investment,
            'total_current_value': total_current_value,
            'total_pnl': total_pnl,
            'return_percentage': return_percentage,
            'positions_count': positions.count(),
            'open_orders_count': orders.count(),
            'positions': PositionSerializer(positions, many=True).data,
            'open_orders': OrderSerializer(orders, many=True).data
        }
        
        return Response(summary, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating portfolio summary for user {request.user.id}: {str(e)}")
        return Response(
            {"error": "Failed to generate portfolio summary. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_market_order(request, order_id):
    """
    Manual execution endpoint for market orders (for testing purposes).
    """
    try:
        account, _ = Account.objects.get_or_create(user=request.user)
        
        try:
            order = Order.objects.get(id=order_id, account=account, status='OPEN')
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found or not open"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mock execution price
        execution_price = request.data.get('execution_price')
        if not execution_price:
            execution_price = 2500  # Mock current market price
        
        # Execute the order
        with transaction.atomic():
            order.status = 'EXECUTED'
            order.executed_at = timezone.now()
            order.save()
            
            # Create trade record
            TradeHistory.objects.create(
                order=order,
                executed_price=execution_price,
                quantity=order.quantity
            )
            
            # Update position and account balance
            serializer = OrderSerializer()
            serializer._update_position(order, execution_price)
            serializer._update_account_balance(order, execution_price)
        
        return Response(
            {
                "message": "Order executed successfully",
                "order": OrderSerializer(order).data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error executing order {order_id} for user {request.user.id}: {str(e)}")
        return Response(
            {"error": "Failed to execute order. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
