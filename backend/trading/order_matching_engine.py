# backend/trading/order_matching_engine.py
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from trading.models import PaperOrder, PaperTrade, PaperPosition, PaperAccount
from marketdata.models import LiveTick

logger = logging.getLogger(__name__)

class OrderMatchingEngine:
    """
    Handles the matching of open paper orders against live market data.
    """

    def __init__(self):
        self.channel_layer = get_channel_layer()

    def run_matching_cycle(self):
        """
        The main entry point to run the order matching process.
        It fetches the latest tick for each symbol with open orders and attempts to execute trades.
        """
        open_orders = PaperOrder.objects.filter(status=PaperOrder.STATUS_OPEN)
        if not open_orders.exists():
            return

        symbols_with_open_orders = open_orders.values_list('symbol', flat=True).distinct()

        for symbol in symbols_with_open_orders:
            latest_tick = LiveTick.objects.filter(symbol=symbol).order_by('-timestamp').first()
            if latest_tick:
                self.process_orders_for_symbol(symbol, Decimal(str(latest_tick.payload.get('ltp', 0))))

    @transaction.atomic
    def process_orders_for_symbol(self, symbol, current_price):
        """
        Processes all open orders for a specific symbol against the current market price.
        """
        if current_price == 0:
            return

        orders_to_process = PaperOrder.objects.select_for_update().filter(
            symbol=symbol,
            status=PaperOrder.STATUS_OPEN
        )

        for order in orders_to_process:
            if self.should_execute(order, current_price):
                self.execute_trade(order, current_price)

    def should_execute(self, order, current_price):
        """
        Determines if an order should be executed based on its type and the current price.
        """
        if order.order_type == PaperOrder.TYPE_MARKET:
            return True
        if order.order_type == PaperOrder.TYPE_LIMIT:
            if order.side == PaperOrder.SIDE_BUY and current_price <= order.price:
                return True
            if order.side == PaperOrder.SIDE_SELL and current_price >= order.price:
                return True
        return False

    def execute_trade(self, order, execution_price):
        """
        Executes a trade, updates the user's account and position,
        and sends real-time updates via WebSocket.
        """
        try:
            account = PaperAccount.objects.get(user=order.user)
            
            # Create the trade record
            trade = PaperTrade.objects.create(
                order=order,
                user=order.user,
                symbol=order.symbol,
                quantity=order.quantity,
                price=execution_price,
                side=order.side,
            )

            # Update the order status
            order.status = PaperOrder.STATUS_EXECUTED
            order.save()

            # Update or create the user's position
            position, created = PaperPosition.objects.get_or_create(
                user=order.user,
                symbol=order.symbol,
                defaults={'quantity': 0, 'average_price': Decimal('0.0')}
            )

            total_value = position.quantity * position.average_price
            if order.side == PaperOrder.SIDE_BUY:
                new_quantity = position.quantity + order.quantity
                total_value += order.quantity * execution_price
                account.balance -= order.quantity * execution_price
            else: # SELL
                new_quantity = position.quantity - order.quantity
                total_value -= order.quantity * execution_price
                account.balance += order.quantity * execution_price

            position.average_price = total_value / new_quantity if new_quantity > 0 else 0
            position.quantity = new_quantity
            
            if position.quantity == 0:
                position.delete()
            else:
                position.save()

            account.save()

            # Broadcast updates to the specific user
            self.broadcast_user_updates(order.user)
            logger.info(f"Successfully executed order {order.id} for user {order.user.username}")

        except PaperAccount.DoesNotExist:
            logger.error(f"Could not find PaperAccount for user {order.user.id} to execute order {order.id}")
        except Exception as e:
            logger.error(f"Error executing trade for order {order.id}: {e}")

    def broadcast_user_updates(self, user):
        """
        Sends a message to the user-specific WebSocket group to trigger a data refresh.
        """
        channel_group_name = f"trading_{user.id}"
        async_to_sync(self.channel_layer.group_send)(
            channel_group_name,
            {
                "type": "trading_update",
                "message": {
                    "event": "UPDATE",
                    "user": user.id,
                },
            },
        )
