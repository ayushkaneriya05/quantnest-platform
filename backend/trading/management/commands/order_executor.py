import time
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from marketdata.mongo_client import get_ticks_collection
from trading.models import Account, Order, Position, TradeHistory


class Command(BaseCommand):
    help = 'Runs the paper trading order execution engine based on delayed ticks.'

    def handle(self, *args, **options):
        self.stdout.write("Starting order execution engine...")
        ticks_collection = get_ticks_collection()

        while True:
            try:
                # 1. Fetch the latest delayed tick to use as the current market price
                fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
                latest_tick_cursor = ticks_collection.find().sort("timestamp", -1).limit(1)
                latest_tick = next(latest_tick_cursor, None)

                if not latest_tick:
                    self.stdout.write("No ticks found in MongoDB. Waiting...")
                    time.sleep(5)
                    continue

                # Group ticks by instrument for efficient processing
                market_prices = {latest_tick['instrument']: Decimal(str(latest_tick['price']))}

                # 2. Fetch all open orders from PostgreSQL
                open_orders = Order.objects.filter(status='OPEN')

                for order in open_orders:
                    instrument_symbol_fyers = f"NSE:{order.instrument.symbol}-EQ"
                    current_price = market_prices.get(instrument_symbol_fyers)

                    if not current_price:
                        continue  # No current price for this instrument, skip

                    # 3. Check if the order should be executed
                    execute_price = None
                    if order.order_type == 'MARKET':
                        execute_price = current_price
                    elif order.order_type == 'LIMIT':
                        if order.transaction_type == 'BUY' and current_price <= order.price:
                            execute_price = current_price
                        elif order.transaction_type == 'SELL' and current_price >= order.price:
                            execute_price = current_price
                    # Add logic for STOP and STOP-LIMIT orders here...

                    if execute_price:
                        self.execute_trade(order, execute_price)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred in the execution loop: {e}"))

            time.sleep(1) # Pause for 1 second before the next loop

    def execute_trade(self, order, execute_price):
        try:
            with transaction.atomic(): # Ensures all DB changes succeed or fail together
                # Lock the account row to prevent race conditions on the balance
                account = Account.objects.select_for_update().get(id=order.account.id)
                
                trade_value = order.quantity * execute_price

                if order.transaction_type == 'BUY':
                    if account.balance < trade_value:
                        self.stdout.write(f"Order {order.id} failed: Insufficient funds.")
                        return # Not enough money, so we don't execute

                    # Update or create position
                    position, created = Position.objects.get_or_create(
                        account=account,
                        instrument=order.instrument,
                        defaults={'quantity': 0, 'average_price': 0}
                    )
                    
                    new_quantity = position.quantity + order.quantity
                    new_total_value = (position.quantity * position.average_price) + trade_value
                    position.average_price = new_total_value / new_quantity
                    position.quantity = new_quantity
                    position.save()

                    # Update account balance
                    account.balance -= trade_value
                    account.save()

                elif order.transaction_type == 'SELL':
                    position = Position.objects.filter(account=account, instrument=order.instrument).first()
                    if not position or position.quantity < order.quantity:
                        self.stdout.write(f"Order {order.id} failed: Not enough shares to sell.")
                        return

                    # Update position
                    position.quantity -= order.quantity
                    if position.quantity == 0:
                        position.delete()
                    else:
                        position.save()

                    # Update account balance
                    account.balance += trade_value
                    account.save()

                # Update order status and log the trade
                order.status = 'EXECUTED'
                order.executed_at = timezone.now()
                order.save()

                TradeHistory.objects.create(
                    order=order,
                    executed_price=execute_price,
                    quantity=order.quantity
                )
                self.stdout.write(self.style.SUCCESS(f"Successfully executed order {order.id} for {order.instrument.symbol}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to execute trade for order {order.id}: {e}"))