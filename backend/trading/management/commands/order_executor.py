# backend/trading/management/commands/order_executor.py

import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
import logging

from marketdata.mongo_client import get_ticks_collection, get_db
from trading.models import Account, Order, Position, TradeHistory
from trading.signals import order_status_changed, position_changed

# Set up a specific logger for this command for better monitoring
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the paper trading order execution engine based on delayed ticks.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting order execution engine..."))
        
        try:
            ticks_collection = get_ticks_collection()
            get_db().command('ping')
            self.stdout.write(self.style.SUCCESS("✅ MongoDB connection successful."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to connect to MongoDB: {e}"))
            return

        while True:
            try:
                market_prices = self.get_latest_market_prices(ticks_collection)

                if not market_prices:
                    self.stdout.write("No recent ticks found. Waiting...")
                    time.sleep(2)
                    continue

                # 1. Check for position-level triggers (SL/TP)
                self.check_position_triggers(market_prices)

                # 2. Process all other open orders
                open_orders = Order.objects.filter(status='OPEN').select_related('account', 'instrument')
                for order in open_orders:
                    current_price = market_prices.get(order.instrument.symbol)
                    if not current_price:
                        continue
                    self.process_order(order, current_price)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred in the execution loop: {e}"))
            
            time.sleep(1)

    def get_latest_market_prices(self, ticks_collection):
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        pipeline = [
            {'$match': {'timestamp': {'$lte': fifteen_minutes_ago}}},
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$instrument',
                'price': {'$first': '$price'},
            }}
        ]
        latest_ticks = list(ticks_collection.aggregate(pipeline))
        return {
            doc['_id'].split(':')[1].split('-')[0]: Decimal(str(doc['price']))
            for doc in latest_ticks
        }

    def check_position_triggers(self, market_prices):
        positions = Position.objects.filter(Q(stop_loss__isnull=False) | Q(take_profit__isnull=False)).select_related('account', 'instrument')
        
        for position in positions:
            current_price = market_prices.get(position.instrument.symbol)
            if not current_price:
                continue

            triggered = False
            if position.stop_loss is not None:
                if (position.quantity > 0 and current_price <= position.stop_loss) or \
                   (position.quantity < 0 and current_price >= position.stop_loss):
                    triggered = True
            
            if not triggered and position.take_profit is not None:
                if (position.quantity > 0 and current_price >= position.take_profit) or \
                   (position.quantity < 0 and current_price <= position.take_profit):
                    triggered = True

            if triggered:
                self.stdout.write(self.style.WARNING(f"Trigger hit for {position.instrument.symbol}. Creating closing order."))
                Order.objects.create(
                    account=position.account,
                    instrument=position.instrument,
                    order_type='MARKET',
                    transaction_type='SELL' if position.quantity > 0 else 'BUY',
                    quantity=abs(position.quantity),
                    status='OPEN'
                )
                position.stop_loss = None
                position.take_profit = None
                position.save()

    def process_order(self, order, current_price):
        execute_price = None
        order_price = Decimal(order.price) if order.price is not None else None
        trigger_price = Decimal(order.trigger_price) if order.trigger_price is not None else None

        if order.order_type == 'MARKET':
            execute_price = current_price
        elif order.order_type == 'LIMIT':
            if (order.transaction_type == 'BUY' and current_price <= order_price) or \
               (order.transaction_type == 'SELL' and current_price >= order_price):
                execute_price = current_price
        elif order.order_type == 'STOP':
            if (order.transaction_type == 'BUY' and current_price >= trigger_price) or \
               (order.transaction_type == 'SELL' and current_price <= trigger_price):
                execute_price = current_price
        elif order.order_type == 'STOP_LIMIT':
            if (order.transaction_type == 'BUY' and current_price >= trigger_price):
                execute_price = min(current_price, order_price)
            elif (order.transaction_type == 'SELL' and current_price <= trigger_price):
                execute_price = max(current_price, order_price)

        if execute_price:
            self.execute_trade(order, execute_price)

    def execute_trade(self, order, execute_price):
        try:
            with transaction.atomic():
                account = Account.objects.select_for_update().get(id=order.account.id)
                position, created = Position.objects.get_or_create(
                    account=account, instrument=order.instrument,
                    defaults={'quantity': 0, 'average_price': Decimal('0.0')}
                )

                trade_value = Decimal(order.quantity) * execute_price
                current_quantity = Decimal(position.quantity)
                order_quantity = Decimal(order.quantity)

                if order.transaction_type == 'BUY':
                    new_total_value = (current_quantity * position.average_price) + trade_value
                    new_quantity = current_quantity + order_quantity
                    position.average_price = new_total_value / new_quantity if new_quantity != 0 else Decimal('0.0')
                    position.quantity = new_quantity
                    account.balance -= trade_value
                elif order.transaction_type == 'SELL':
                    pnl = (execute_price - position.average_price) * min(order_quantity, current_quantity)
                    account.realized_pnl += pnl
                    new_quantity = current_quantity - order_quantity
                    position.quantity = new_quantity
                    account.balance += trade_value

                position_to_send = None
                if position.quantity == 0:
                    # FIX: Prepare a payload for the signal before deleting the object
                    position_to_send = {'id': position.id, 'quantity': 0, 'instrument': {'symbol': position.instrument.symbol}}
                    position.delete()
                else:
                    position.save()
                    position_to_send = position
                
                account.save()

                order.status = 'COMPLETE'
                order.executed_at = timezone.now()
                order.save()

                TradeHistory.objects.create(
                    order=order, executed_price=execute_price,
                    quantity=order.quantity, timestamp=order.executed_at
                )
                
                order_status_changed.send(sender=self.__class__, order=order)
                if position_to_send:
                    position_changed.send(sender=self.__class__, position=position_to_send, user_id=account.user.id)

                self.stdout.write(self.style.SUCCESS(f"EXECUTED order {order.id}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed transaction for order {order.id}: {e}"))
            order.status = 'REJECTED'
            order.save()
            order_status_changed.send(sender=self.__class__, order=order)
