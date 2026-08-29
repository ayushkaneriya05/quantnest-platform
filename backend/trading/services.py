from decimal import Decimal
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from instruments.models import Instrument
from marketdata.live_feed import LiveMarketDataRegistry

from .models import Account, Order, Position, TradeHistory, Watchlist, ClosedPositionLog
from .signals import order_status_changed, position_changed


class TradingInstrumentService:
    @staticmethod
    def search(query, equity_only=False):
        if len(query or "") < 2:
            return Instrument.objects.none()
        
        qs = Instrument.objects.filter(is_active=True)
        
        if equity_only:
            # Strict filter for NSE Equities and Indexes
            qs = qs.filter(exchange='NSE', segment=10, instrument_type__in=['STOCK', 'INDEX'])

        from django.db.models import Case, When, Value, IntegerField
        from datetime import date
        
        # Filter out expired contracts
        qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=date.today()))

        qs = qs.filter(
            Q(symbol__icontains=query)
            | Q(name__icontains=query)
            | Q(sym_ticker__icontains=query)
        ).annotate(
            match_score=Case(
                When(symbol__iexact=query, then=Value(1)),
                When(symbol__istartswith=query, then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by('match_score', 'symbol')
        
        return qs[:20]

    @staticmethod
    def get_by_symbol(symbol):
        return get_object_or_404(
            Instrument,
            Q(symbol=symbol) | Q(sym_ticker=symbol) | Q(sym_ticker=f"NSE:{symbol}-EQ"),
        )


class TradingAccountService:
    @staticmethod
    def get_or_create_account(user):
        return Account.objects.get_or_create(user=user)[0]


class TradingWatchlistService:
    @staticmethod
    def get_watchlist(user):
        return Watchlist.objects.get_or_create(user=user)[0]

    @classmethod
    def add_instrument(cls, user, instrument_id):
        watchlist = cls.get_watchlist(user)
        instrument = get_object_or_404(Instrument, id=instrument_id)
        watchlist.instruments.add(instrument)
        return watchlist

    @classmethod
    def remove_instrument(cls, user, instrument_id):
        watchlist = cls.get_watchlist(user)
        instrument = get_object_or_404(Instrument, id=instrument_id)
        watchlist.instruments.remove(instrument)
        return watchlist


class TradingOrderService:
    PRICE_REQUIRED_TYPES = {"LIMIT", "STOP_LIMIT"}
    TRIGGER_REQUIRED_TYPES = {"STOP", "STOP_LIMIT"}
    MARKET_QUOTE_MAX_AGE_SECONDS = int(getattr(settings, "TRADING_MAX_QUOTE_AGE_SECONDS", 30))

    @classmethod
    def validate_payload(cls, data):
        order_type = data.get("order_type")
        quantity = int(data.get("quantity") or 0)

        if order_type not in dict(Order.ORDER_TYPES):
            raise ValueError("Unsupported order type.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if order_type in cls.PRICE_REQUIRED_TYPES and not data.get("price"):
            raise ValueError(f"price is required for {order_type} orders.")

        if order_type in cls.TRIGGER_REQUIRED_TYPES and not data.get("trigger_price"):
            raise ValueError(f"trigger_price is required for {order_type} orders.")

        return data

    @classmethod
    def _quote_age_seconds(cls, quote):
        raw_timestamp = quote.get("updated_at") or quote.get("timestamp")
        if not raw_timestamp:
            return None
        if isinstance(raw_timestamp, (int, float)):
            return max(0, timezone.now().timestamp() - float(raw_timestamp))
        parsed = parse_datetime(str(raw_timestamp))
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, dt_timezone.utc)
        return max(0, (timezone.now() - parsed).total_seconds())

    @classmethod
    def get_market_fill_price(cls, instrument):
        from marketdata.services import MarketStatusService

        if not MarketStatusService.is_market_open():
            raise ValidationError("Market is currently closed. Market orders are only allowed during trading hours.")

        symbol = instrument.sym_ticker or instrument.symbol
        from marketdata.quote_store import QuoteStore
        quote = QuoteStore.get_latest(symbol)
        
        if not quote:
            # Fallback to live API, then DB storage
            from marketdata.services import MarketDataService
            quote = MarketDataService.get_live_quote_from_fyers(symbol)
            if not quote:
                quote = MarketDataService.latest_quote_from_storage(symbol)

        price = quote.get("price") if quote else None
        if price in (None, "", 0, "0"):
            raise ValidationError("Live quote is unavailable. Market order was not placed.")

        age_seconds = cls._quote_age_seconds(quote)
        if age_seconds is not None and age_seconds > cls.MARKET_QUOTE_MAX_AGE_SECONDS:
            raise ValidationError("Live quote is stale. Please wait for a fresh tick before placing a market order.")

        return Decimal(str(price))

    @classmethod
    def create_order(cls, user, validated_data):
        cls.validate_payload(validated_data)
        instrument_symbol = validated_data.pop("instrument_symbol")
        account = TradingAccountService.get_or_create_account(user)
        instrument = Instrument.objects.filter(
            Q(symbol=instrument_symbol.upper())
            | Q(sym_ticker=instrument_symbol.upper())
            | Q(sym_ticker__icontains=f":{instrument_symbol.upper()}-")
        ).first()

        if instrument is None:
            raise ValueError("Instrument symbol was not found.")

        # Ensure symbol is tracked in live market data
        try:
            LiveMarketDataRegistry.add_symbols([instrument.sym_ticker or instrument.symbol])
        except Exception:
            pass

        fill_price = None
        if validated_data.get("order_type") == "MARKET":
            fill_price = cls.get_market_fill_price(instrument)

        order = Order.objects.create(account=account, instrument=instrument, **validated_data)

        # Immediate execution for MARKET orders with a fresh live quote.
        if order.order_type == "MARKET":
            cls.execute_order(order, fill_price)

        return order

    @classmethod
    @transaction.atomic
    def execute_order(cls, order, fill_price):
        order = (
            Order.objects.select_for_update()
            .select_related("account", "instrument")
            .get(pk=order.pk)
        )
        if order.status != "OPEN":
            return order

        account = Account.objects.select_for_update().get(pk=order.account_id)
        quantity = order.quantity
        order_value = fill_price * quantity

        if order.transaction_type == "BUY" and account.balance < order_value:
            order.status = "REJECTED"
            order.save(update_fields=["status"])
            order_status_changed.send(sender=cls, order=order)
            return order

        try:
            position = Position.objects.select_for_update().get(
                account=account,
                instrument=order.instrument,
            )
        except Position.DoesNotExist:
            position = Position(
                account=account,
                instrument=order.instrument,
                quantity=0,
                average_price=Decimal("0"),
            )

        old_quantity = position.quantity
        transaction_qty = quantity if order.transaction_type == "BUY" else -quantity
        new_quantity = old_quantity + transaction_qty

        account.balance -= (Decimal(str(transaction_qty)) * fill_price)
        
        if old_quantity > 0 and transaction_qty < 0:
            closed_qty = min(abs(old_quantity), abs(transaction_qty))
            pnl = (fill_price - position.average_price) * Decimal(str(closed_qty))
            account.realized_pnl += pnl
            
            ClosedPositionLog.objects.create(
                account=account,
                instrument=order.instrument,
                side="LONG",
                quantity=closed_qty,
                entry_price=position.average_price,
                exit_price=fill_price,
                realized_pnl=pnl,
                entry_time=position.created_at
            )
            
        elif old_quantity < 0 and transaction_qty > 0:
            closed_qty = min(abs(old_quantity), abs(transaction_qty))
            pnl = (position.average_price - fill_price) * Decimal(str(closed_qty))
            account.realized_pnl += pnl
            
            ClosedPositionLog.objects.create(
                account=account,
                instrument=order.instrument,
                side="SHORT",
                quantity=closed_qty,
                entry_price=position.average_price,
                exit_price=fill_price,
                realized_pnl=pnl,
                entry_time=position.created_at
            )

        if new_quantity == 0:
            position.quantity = 0
            cls.sync_position_sl_tp_orders(position)
            if position.pk:
                position.delete()
        else:
            if (old_quantity >= 0 and transaction_qty > 0) or (old_quantity <= 0 and transaction_qty < 0):
                total_cost = (abs(old_quantity) * position.average_price) + (abs(transaction_qty) * fill_price)
                position.average_price = total_cost / abs(new_quantity)
            elif old_quantity != 0 and (old_quantity > 0 > new_quantity or old_quantity < 0 < new_quantity):
                # Reversal: the remaining open leg starts at the reversal fill price.
                position.average_price = fill_price
            elif old_quantity == 0:
                position.average_price = fill_price
            
            position.quantity = new_quantity
            position.save()

        account.margin = cls.calculate_used_margin(account)
        account.save()

        # Update Order
        order.status = "COMPLETE"
        order.executed_at = timezone.now()
        order.price = fill_price # Store the actual fill price
        order.save(update_fields=["status", "executed_at", "price"])
        
        # Handle OCO Cancellation
        if order.is_oco and order.oco_linked_order_id:
            linked_order = Order.objects.filter(pk=order.oco_linked_order_id, status="OPEN").first()
            if linked_order:
                cls.cancel_order(linked_order)

        # Create Trade History
        TradeHistory.objects.create(
            order=order,
            executed_price=fill_price,
            quantity=quantity,
        )

        # Emit Signals
        order_status_changed.send(sender=cls, order=order)
        position_changed.send(sender=cls, position=position if new_quantity != 0 else None, user_id=account.user.id)
        
        # Dynamically sync the Position's SL/TP exit orders based on the new quantity (if not already handled by deletion)
        if new_quantity != 0:
            cls.sync_position_sl_tp_orders(position)
        
        return order

    @classmethod
    def process_matching_engine(cls, symbol, tick_data, open_orders=None):
        """
        Process matching engine logic for a given symbol and tick data.
        """
        # Gate: Never execute orders when the market is closed.
        # Stale ticks from broker WebSockets can arrive on weekends/holidays.
        from marketdata.services import MarketStatusService
        if not MarketStatusService.is_market_open():
            return

        raw_price = tick_data.get("price")
        if raw_price in (None, "", 0, "0"):
            return
        ltp = Decimal(str(raw_price))
        
        # --- Process Open Orders ---
        if open_orders is None:
            open_orders = Order.objects.filter(
                instrument__sym_ticker=symbol,
                status="OPEN"
            ).select_related("account", "instrument")

        for order in open_orders:
            should_fill = False
            
            if order.order_type == "MARKET":
                should_fill = True

            elif order.order_type == "LIMIT":
                if order.transaction_type == "BUY" and ltp <= order.price:
                    should_fill = True
                elif order.transaction_type == "SELL" and ltp >= order.price:
                    should_fill = True
            
            elif order.order_type == "STOP":
                if order.transaction_type == "BUY" and ltp >= order.trigger_price:
                    should_fill = True
                elif order.transaction_type == "SELL" and ltp <= order.trigger_price:
                    should_fill = True

            elif order.order_type == "STOP_LIMIT":
                if order.transaction_type == "BUY" and ltp >= order.trigger_price:
                    order.order_type = "LIMIT"
                    order.trigger_price = None
                    order.save(update_fields=["order_type", "trigger_price"])
                    if ltp <= order.price:
                        should_fill = True
                elif order.transaction_type == "SELL" and ltp <= order.trigger_price:
                    order.order_type = "LIMIT"
                    order.trigger_price = None
                    order.save(update_fields=["order_type", "trigger_price"])
                    if ltp >= order.price:
                        should_fill = True

            if should_fill:
                cls.execute_order(order, ltp)


    @staticmethod
    def cancel_order(order):
        order.status = "CANCELLED"
        order.save(update_fields=["status"])
        
        # Bidirectional Sync: If a user manually cancels an SL/TP exit order, clear it from the position
        if order.position_link_id:
            position = order.position_link
            if order.order_type == "STOP":
                position.stop_loss = None
            elif order.order_type == "LIMIT":
                position.take_profit = None
            position.save(update_fields=["stop_loss", "take_profit"])
            
        order_status_changed.send(sender=TradingOrderService, order=order)
        return order
        
    @classmethod
    def sync_position_sl_tp_orders(cls, position):
        """
        Synchronizes Position SL/TP fields to real pending OCO (One Cancels Other) orders.
        """
        qty = position.quantity
        account = position.account
        instrument = position.instrument
        
        # 1. Fetch existing exit orders linked to this position
        existing_orders = list(Order.objects.filter(position_link=position, status="OPEN"))
        
        if qty == 0:
            # Position closed: Cancel all pending exit orders
            for pending_order in existing_orders:
                cls.cancel_order(pending_order)
            return
            
        exit_transaction_type = "SELL" if qty > 0 else "BUY"
        exit_quantity = abs(qty)
        
        # Find existing STOP and LIMIT
        stop_order = next((o for o in existing_orders if o.order_type == "STOP"), None)
        limit_order = next((o for o in existing_orders if o.order_type == "LIMIT"), None)
        
        # Process Stop Loss
        if position.stop_loss:
            if stop_order:
                if stop_order.trigger_price != position.stop_loss or stop_order.quantity != exit_quantity or stop_order.transaction_type != exit_transaction_type:
                    stop_order.trigger_price = position.stop_loss
                    stop_order.quantity = exit_quantity
                    stop_order.transaction_type = exit_transaction_type
                    stop_order.save(update_fields=["trigger_price", "quantity", "transaction_type"])
            else:
                stop_order = Order.objects.create(
                    account=account,
                    instrument=instrument,
                    order_type="STOP",
                    status="OPEN",
                    transaction_type=exit_transaction_type,
                    quantity=exit_quantity,
                    trigger_price=position.stop_loss,
                    position_link=position,
                    is_oco=True if position.take_profit else False
                )
        elif stop_order:
            cls.cancel_order(stop_order)
            stop_order = None
            
        # Process Take Profit
        if position.take_profit:
            if limit_order:
                if limit_order.price != position.take_profit or limit_order.quantity != exit_quantity or limit_order.transaction_type != exit_transaction_type:
                    limit_order.price = position.take_profit
                    limit_order.quantity = exit_quantity
                    limit_order.transaction_type = exit_transaction_type
                    limit_order.save(update_fields=["price", "quantity", "transaction_type"])
            else:
                limit_order = Order.objects.create(
                    account=account,
                    instrument=instrument,
                    order_type="LIMIT",
                    status="OPEN",
                    transaction_type=exit_transaction_type,
                    quantity=exit_quantity,
                    price=position.take_profit,
                    position_link=position,
                    is_oco=True if position.stop_loss else False
                )
        elif limit_order:
            cls.cancel_order(limit_order)
            limit_order = None
            
        # Secure OCO Links
        if stop_order and limit_order:
            if stop_order.oco_linked_order_id != limit_order.id:
                stop_order.oco_linked_order = limit_order
                stop_order.is_oco = True
                stop_order.save(update_fields=["oco_linked_order", "is_oco"])
            if limit_order.oco_linked_order_id != stop_order.id:
                limit_order.oco_linked_order = stop_order
                limit_order.is_oco = True
                limit_order.save(update_fields=["oco_linked_order", "is_oco"])
        elif stop_order and stop_order.is_oco:
            stop_order.is_oco = False
            stop_order.oco_linked_order = None
            stop_order.save(update_fields=["is_oco", "oco_linked_order"])
        elif limit_order and limit_order.is_oco:
            limit_order.is_oco = False
            limit_order.oco_linked_order = None
            limit_order.save(update_fields=["is_oco", "oco_linked_order"])

    @classmethod
    def sync_order_to_position(cls, order):
        """
        Reverse Sync: If a user manually updates the price of a pending SL/TP exit order,
        this updates the underlying Position so the chart UI stays perfectly synced.
        """
        if not order.position_link_id:
            return
            
        position = order.position_link
        if order.order_type == "STOP":
            position.stop_loss = order.trigger_price
            position.save(update_fields=["stop_loss"])
        elif order.order_type == "LIMIT":
            position.take_profit = order.price
            position.save(update_fields=["take_profit"])

    @staticmethod
    def calculate_used_margin(account):
        total = Decimal("0")
        for position in Position.objects.filter(account=account):
            if position.quantity < 0:
                total += Decimal(abs(position.quantity)) * Decimal(position.average_price)
        return total

    @classmethod
    def unrealized_pnl_for_position(cls, position):
        symbol = position.instrument.sym_ticker or position.instrument.symbol
        from marketdata.quote_store import QuoteStore
        quote = QuoteStore.get_latest(symbol)
        
        if not quote:
            from marketdata.services import MarketDataService
            quote = MarketDataService.get_live_quote_from_fyers(symbol)
            if not quote:
                quote = MarketDataService.latest_quote_from_storage(symbol)
            
        price = quote.get("price") if quote else None
        if price in (None, "", 0, "0"):
            price = position.average_price
        current_price = Decimal(str(price))
        quantity = Decimal(str(position.quantity))
        return (current_price - Decimal(position.average_price)) * quantity, current_price


class PaperTradingTerminalService:
    @classmethod
    def build_snapshot(cls, user):
        account = (
            Account.objects.prefetch_related(
                "positions__instrument",
                "orders__instrument",
                Prefetch(
                    "orders__trades",
                    queryset=TradeHistory.objects.select_related("order", "order__instrument").order_by("-timestamp"),
                ),
            )
            .filter(user=user)
            .first()
        )

        if account is None:
            account = TradingAccountService.get_or_create_account(user)

        watchlist = TradingWatchlistService.get_watchlist(user)
        positions = list(
            Position.objects.filter(account=account).select_related("instrument").order_by("instrument__symbol")
        )
        computed_margin = TradingOrderService.calculate_used_margin(account)
        if account.margin != computed_margin:
            account.margin = computed_margin
            account.save(update_fields=["margin"])
        orders = list(Order.objects.filter(account=account).select_related("instrument").order_by("-created_at"))
        open_orders = [order for order in orders if order.status == "OPEN"]
        trades = list(
            TradeHistory.objects.filter(order__account=account)
            .select_related("order", "order__instrument")
            .order_by("-timestamp")[:20]
        )

        return {
            "account": cls.serialize_account(account, positions),
            "watchlist": cls.serialize_watchlist(watchlist),
            "positions": [cls.serialize_position(position) for position in positions],
            "open_orders": [cls.serialize_order(order) for order in open_orders],
            "recent_trades": [cls.serialize_trade(trade) for trade in trades],
        }

    @staticmethod
    def serialize_account(account, positions):
        market_value = Decimal("0")
        unrealized_pnl = Decimal("0")
        for position in positions:
            position_pnl, current_price = TradingOrderService.unrealized_pnl_for_position(position)
            unrealized_pnl += position_pnl
            market_value += current_price * abs(position.quantity)

        return {
            "id": account.id,
            "balance": str(account.balance),
            "margin": str(account.margin),
            "realized_pnl": str(account.realized_pnl),
            "unrealized_pnl": str(unrealized_pnl),
            "market_value": str(market_value),
            "created_at": account.created_at.isoformat(),
        }

    @staticmethod
    def serialize_watchlist(watchlist):
        instruments = watchlist.instruments.all().order_by("symbol")
        return [
            {
                "id": instrument.id,
                "symbol": instrument.symbol,
                "sym_ticker": instrument.sym_ticker,
                "company_name": instrument.name,
            }
            for instrument in instruments
        ]

    @staticmethod
    def serialize_position(position):
        position_pnl, current_price = TradingOrderService.unrealized_pnl_for_position(position)
        return {
            "id": position.id,
            "instrument": {
                "id": position.instrument.id,
                "symbol": position.instrument.symbol,
                "company_name": position.instrument.name,
            },
            "quantity": position.quantity,
            "average_price": str(position.average_price),
            "current_price": str(current_price),
            "unrealized_pnl": str(position_pnl),
            "stop_loss": str(position.stop_loss) if position.stop_loss is not None else None,
            "take_profit": str(position.take_profit) if position.take_profit is not None else None,
        }

    @staticmethod
    def serialize_order(order):
        return {
            "id": order.id,
            "instrument": {
                "id": order.instrument.id,
                "symbol": order.instrument.symbol,
                "company_name": order.instrument.name,
            },
            "order_type": order.order_type,
            "status": order.status,
            "transaction_type": order.transaction_type,
            "quantity": order.quantity,
            "price": str(order.price) if order.price is not None else None,
            "trigger_price": str(order.trigger_price) if order.trigger_price is not None else None,
            "created_at": order.created_at.isoformat(),
            "executed_at": order.executed_at.isoformat() if order.executed_at else None,
        }

    @staticmethod
    def serialize_trade(trade):
        return {
            "id": trade.id,
            "order": trade.order_id,
            "instrument": {
                "id": trade.order.instrument.id,
                "symbol": trade.order.instrument.symbol,
                "company_name": trade.order.instrument.name,
            },
            "transaction_type": trade.order.transaction_type,
            "order_type": trade.order.order_type,
            "executed_price": str(trade.executed_price),
            "quantity": trade.quantity,
            "timestamp": trade.timestamp.isoformat(),
        }
