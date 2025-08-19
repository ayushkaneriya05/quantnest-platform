import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging

from marketdata.mongo_client import get_ticks_collection, get_db
from trading.models import Account, Order, Position, TradeHistory, Instrument

# Set up a specific logger for this command for better monitoring
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the paper trading order execution engine based on delayed ticks.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting order execution engine..."))
        
        # Establish a persistent connection to MongoDB
        try:
            ticks_collection = get_ticks_collection()
            # Ping the server to ensure the connection is live
            get_db().command('ping')
            self.stdout.write(self.style.SUCCESS("✅ MongoDB connection successful."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to connect to MongoDB: {e}"))
            return

        while True:
            try:
                # 1. Fetch the latest delayed ticks for all instruments
                # This is more efficient than querying one-by-one inside the loop
                market_prices = self.get_latest_market_prices(ticks_collection)

                if not market_prices:
                    self.stdout.write("No recent ticks found. Waiting...")
                    time.sleep(2)
                    continue

                # 2. Fetch all open orders from PostgreSQL
                # We select related account and instrument to reduce DB queries inside the loop
                open_orders = Order.objects.filter(status='OPEN').select_related('account', 'instrument')

                for order in open_orders:
                    current_price = market_prices.get(order.instrument.symbol)

                    if not current_price:
                        continue # No current price for this instrument, skip to the next order

                    # 3. Determine if the order should be executed based on its type
                    self.process_order(order, current_price)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred in the execution loop: {e}"))
                # In a real production scenario, you might want to alert an admin here

            time.sleep(1) # Pause for 1 second before the next loop

    def get_latest_market_prices(self, ticks_collection):
        """
        Fetches the most recent price for each instrument from the delayed tick stream.
        """
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        
        pipeline = [
            {'$match': {'timestamp': {'$lte': fifteen_minutes_ago}}},
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$instrument',
                'price': {'$first': '$price'},
                'timestamp': {'$first': '$timestamp'}
            }}
        ]
        
        latest_ticks = list(ticks_collection.aggregate(pipeline))
        
        # Fyers symbols are like 'NSE:RELIANCE-EQ', we want just 'RELIANCE'
        return {
            doc['_id'].split(':')[1].split('-')[0]: Decimal(str(doc['price']))
            for doc in latest_ticks
        }

    def process_order(self, order, current_price):
        """Checks an order against the current market price and executes it if conditions are met."""
        execute_price = None
        
        try:
            order_price = Decimal(order.price) if order.price is not None else None
            trigger_price = Decimal(order.trigger_price) if order.trigger_price is not None else None

            # --- Order Logic ---
            if order.order_type == 'MARKET':
                execute_price = current_price
            
            elif order.order_type == 'LIMIT':
                if order.transaction_type == 'BUY' and current_price <= order_price:
                    execute_price = current_price
                elif order.transaction_type == 'SELL' and current_price >= order_price:
                    execute_price = current_price

            elif order.order_type == 'STOP':
                if order.transaction_type == 'BUY' and current_price >= trigger_price:
                    execute_price = current_price # Execute as a market order
                elif order.transaction_type == 'SELL' and current_price <= trigger_price:
                    execute_price = current_price # Execute as a market order

            elif order.order_type == 'STOP_LIMIT':
                if order.transaction_type == 'BUY' and current_price >= trigger_price:
                    # The stop has been triggered, now it's a limit order
                    execute_price = min(current_price, order_price)
                elif order.transaction_type == 'SELL' and current_price <= trigger_price:
                    # The stop has been triggered, now it's a limit order
                    execute_price = max(current_price, order_price)

            if execute_price:
                self.execute_trade(order, execute_price)

        except (InvalidOperation, TypeError) as e:
             self.stderr.write(self.style.ERROR(f"Could not process order {order.id} due to invalid price data: {e}"))


    def execute_trade(self, order, execute_price):
        """
        Executes a trade within a database transaction to ensure data integrity.
        """
        try:
            with transaction.atomic():
                # Lock the account row to prevent race conditions (e.g., two trades executing simultaneously)
                account = Account.objects.select_for_update().get(id=order.account.id)
                
                trade_value = Decimal(order.quantity) * execute_price

                if order.transaction_type == 'BUY':
                    if account.balance < trade_value:
                        logger.warning(f"Order {order.id} for user {account.user.id} failed: Insufficient funds.")
                        # Optionally, you could cancel the order here
                        # order.status = 'CANCELLED'
                        # order.save()
                        return

                    # Update or create the position
                    position, created = Position.objects.get_or_create(
                        account=account,
                        instrument=order.instrument,
                        defaults={'quantity': 0, 'average_price': Decimal('0.0')}
                    )
                    
                    new_quantity = position.quantity + order.quantity
                    new_total_value = (Decimal(position.quantity) * position.average_price) + trade_value
                    position.average_price = new_total_value / new_quantity
                    position.quantity = new_quantity
                    position.save()

                    # Update account balance
                    account.balance -= trade_value
                    account.save()

                elif order.transaction_type == 'SELL':
                    position = Position.objects.filter(account=account, instrument=order.instrument).first()
                    if not position or position.quantity < order.quantity:
                        logger.warning(f"Order {order.id} for user {account.user.id} failed: Not enough shares to sell.")
                        return

                    position.quantity -= order.quantity
                    if position.quantity == 0:
                        position.delete()
                    else:
                        position.save()

                    account.balance += trade_value
                    account.save()

                # Mark order as executed and log the trade
                order.status = 'EXECUTED'
                order.executed_at = timezone.now()
                order.save()

                TradeHistory.objects.create(
                    order=order,
                    executed_price=execute_price,
                    quantity=order.quantity,
                    timestamp=order.executed_at
                )
                logger.info(f"EXECUTED order {order.id}: {order.transaction_type} {order.quantity} {order.instrument.symbol} @ {execute_price}")
                self.stdout.write(self.style.SUCCESS(f"Processed order {order.id}"))

        except Account.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"CRITICAL: Account not found for order {order.id}. Skipping."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed during transaction for order {order.id}: {e}"))