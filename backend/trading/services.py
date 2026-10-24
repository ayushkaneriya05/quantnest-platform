from common.enums import (
    InstrumentType,
    TerminalOrderStatus, Side, TERMINAL_USER_ORDER_TYPES,
    TERMINAL_PRICE_REQUIRED_TYPES, TERMINAL_TRIGGER_REQUIRED_TYPES,
)
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from instruments.models import Instrument

from .models import Account, Order, Position, Watchlist
from .signals import order_status_changed
from common.costs import snapshot_charge_profile
from execution.preparation import contract_from_instrument
from marketdata.calendar import MarketSessionCalendar


class TradingInstrumentService:
    @staticmethod
    def search(query, *, exchange='', instrument_type='', expiry_date=None):
        query = (query or "").strip()
        
        qs = Instrument.objects.filter(is_active=True)
        if exchange:
            qs = qs.filter(exchange=exchange)
        if instrument_type:
            qs = qs.filter(instrument_type=instrument_type)
        if expiry_date:
            qs = qs.filter(expiry_date=expiry_date)
        
        qs = qs.exclude(instrument_type=InstrumentType.MF)

        from django.db.models import Case, When, Value, IntegerField
        from datetime import date
        
        # Filter out expired contracts
        qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=date.today()))

        if not query:
            return qs.order_by('expiry_date', 'sym_ticker')[:50]

        qs = qs.filter(
            Q(symbol__icontains=query)
            | Q(name__icontains=query)
            | Q(sym_ticker__icontains=query)
            | Q(underlying_symbol__icontains=query)
        ).annotate(
            match_score=Case(
                When(sym_ticker__iexact=query, then=Value(1)),
                When(name__iexact=query, then=Value(2)),
                When(symbol__iexact=query, then=Value(3)),
                When(sym_ticker__istartswith=query, then=Value(4)),
                When(name__icontains=query, then=Value(6)),
                When(symbol__istartswith=query, then=Value(5)),
                default=Value(100),
                output_field=IntegerField()
            )
        ).order_by('match_score', 'sym_ticker')
        
        return qs[:50]

class TradingAccountService:
    @staticmethod
    def get_or_create_account(user):
        return Account.objects.get_or_create(user=user)[0]


class TradingWatchlistService:
    @staticmethod
    def get_watchlist(user, watchlist_id=0):
        if watchlist_id:
            return get_object_or_404(Watchlist, user=user, pk=watchlist_id)
        return Watchlist.objects.filter(user=user).order_by('id').first() or Watchlist.objects.get_or_create(user=user, name='Main')[0]

    @classmethod
    def add_instrument(cls, user, sym_ticker, watchlist_id=0):
        watchlist = cls.get_watchlist(user, watchlist_id)
        instrument = get_object_or_404(Instrument, sym_ticker=sym_ticker)
        watchlist.instruments.add(instrument)
        return watchlist

    @classmethod
    def remove_instrument(cls, user, sym_ticker, watchlist_id=0):
        watchlist = cls.get_watchlist(user, watchlist_id)
        instrument = get_object_or_404(Instrument, sym_ticker=sym_ticker)
        watchlist.instruments.remove(instrument)
        return watchlist


class TradingOrderService:

    @staticmethod
    def validate_payload(data):
        order_type = data.get("order_type")
        quantity = int(data.get("quantity") or 0)

        if order_type not in TERMINAL_USER_ORDER_TYPES:
            raise ValueError("Unsupported order type.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if order_type in TERMINAL_PRICE_REQUIRED_TYPES and not data.get("price"):
            raise ValueError(f"price is required for {order_type} orders.")

        if order_type in TERMINAL_TRIGGER_REQUIRED_TYPES and not data.get("trigger_price"):
            raise ValueError(f"trigger_price is required for {order_type} orders.")

        return data

    @classmethod
    def get_market_fill_price(cls, instrument):
        from marketdata.shared_memory import get_market_price
        cls.require_session(instrument)
        price = get_market_price(instrument.sym_ticker)
        if price is None:
            raise ValidationError("A market observation is required. Wait for the connected feed before placing a market order.")
        return Decimal(str(price))

    @staticmethod
    def pending_cash(account, exclude_id=None):
        orders = Order.objects.filter(account=account, status=TerminalOrderStatus.OPEN)
        if exclude_id:
            orders = orders.exclude(pk=exclude_id)
        return orders.aggregate(total=Sum("reserved_cash"))["total"] or Decimal("0")


    @classmethod
    def required_cash(cls, order, account, price):
        from execution.ledger import margin
        from execution.preparation import contract_from_instrument
        from execution.types import Account as FinancialAccount
        from common.enums import ExecutionMode
        if order.reduce_only:
            return Decimal('0')
        position = Position.objects.filter(account=account, instrument=order.instrument).first()
        signed = order.quantity if order.transaction_type == Side.BUY else -order.quantity
        reducing = 0
        if position and position.quantity * signed < 0:
            pending = Order.objects.filter(account=account, instrument=order.instrument,
                status=TerminalOrderStatus.OPEN, transaction_type=order.transaction_type).exclude(pk=order.pk)
            already = pending.aggregate(total=Sum('quantity'))['total'] or 0
            reducing = min(max(abs(position.quantity) - already, 0), order.quantity)
        state = FinancialAccount((ExecutionMode.TERMINAL, account.pk), account.balance,
            futures_margin_pct=account.futures_margin_pct, short_option_margin_pct=account.short_option_margin_pct)
        return margin(state, contract_from_instrument(order.instrument),
            (order.quantity - reducing) * (1 if signed > 0 else -1), price)

    @classmethod
    @transaction.atomic
    def create_order(cls, user, validated_data):
        from uuid import uuid4
        from execution.preparation import contract_from_instrument
        from execution.repository import enqueue
        from common.enums import ExecutionMode, ExecutionCommandType
        cls.validate_payload(validated_data)
        data = dict(validated_data)
        instrument = data.pop('instrument')
        account = TradingAccountService.get_or_create_account(user)
        account = Account.objects.select_for_update().get(pk=account.pk)
        if not user.is_active:
            raise ValidationError("This account is inactive.")
        calendar = cls.require_session(instrument)
        contract_from_instrument(instrument).validate(data['quantity'],
            tuple(data.get(key) for key in ('price', 'trigger_price', 'stop_loss', 'take_profit')),
            timezone.now().astimezone(calendar.zone))
        order = Order.objects.create(account=account, instrument=instrument, request_id=uuid4(),
            charge_profile_snapshot=snapshot_charge_profile(account.charge_profile), **data)
        enqueue(ExecutionMode.TERMINAL, account.pk, ExecutionCommandType.ORDER, {
            'instrument_id': instrument.pk, 'side': order.transaction_type, 'quantity': order.quantity,
            'order_type': order.order_type, 'limit_price': order.price, 'trigger_price': order.trigger_price,
            'stop_loss': order.stop_loss, 'take_profit': order.take_profit,
            'reduce_only': order.reduce_only, 'reason': 'Manual order',
        }, request_id=order.request_id)
        order_status_changed.send(sender=cls, order=order)
        return order


    @staticmethod
    @transaction.atomic
    def cancel_order(order):
        from execution.repository import enqueue
        from common.enums import ExecutionMode, ExecutionCommandType
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != TerminalOrderStatus.OPEN:
            return order
        enqueue(ExecutionMode.TERMINAL, order.account_id, ExecutionCommandType.CANCEL,
            {'identity': str(order.request_id)})
        return order
        


    @staticmethod
    def require_session(instrument):
        try:
            calendar = MarketSessionCalendar.for_instrument(instrument)
            calendar.require_open(timezone.now())
        except ValueError as exc:
            raise ValidationError(str(exc)) from None
        return calendar

    @staticmethod
    def position_margin(account, instrument, quantity, price):
        from execution.ledger import margin
        from execution.preparation import contract_from_instrument
        from execution.types import Account as FinancialAccount
        from common.enums import ExecutionMode
        state = FinancialAccount((ExecutionMode.TERMINAL, account.pk), account.balance,
            futures_margin_pct=account.futures_margin_pct, short_option_margin_pct=account.short_option_margin_pct)
        contract = contract_from_instrument(instrument)
        collateral = margin(state, contract, quantity, price)
        if instrument.instrument_type == InstrumentType.FUTURE:
            return collateral
        return collateral + contract.value(price, -quantity) if quantity < 0 else Decimal('0')




    @staticmethod
    def get_position_mark(position):
        """Valuation can use a stored close; execution requires an observed tick."""
        from marketdata.quotes import read_quote
        quote = read_quote(position.instrument.sym_ticker)
        price, at, source = (
            (Decimal(str(quote["price"])), quote["timestamp"], quote["source"]) if quote["available"] else
            (position.average_price, position.created_at.isoformat(), "entry")
        )
        pnl = contract_from_instrument(position.instrument).value(price - position.average_price, position.quantity)
        return {'price': price, 'pnl': pnl, 'at': at, 'source': source}



class TradingTerminalService:
    @staticmethod
    def build_snapshot(user, watchlist_id=0):
        from .serializers import InstrumentSerializer, OrderSerializer, PositionSerializer

        account = TradingAccountService.get_or_create_account(user)
        watchlist = TradingWatchlistService.get_watchlist(user, watchlist_id)
        positions = list(Position.objects.filter(account=account).select_related("instrument").order_by("instrument__name", "id"))
        orders = list(Order.objects.filter(account=account, status=TerminalOrderStatus.OPEN).select_related("instrument").order_by("-created_at"))

        position_data = PositionSerializer(positions, many=True).data
        unrealized_pnl = market_value = margin = Decimal("0")
        for position, row in zip(positions, position_data):
            mark = TradingOrderService.get_position_mark(position)
            pnl, price = mark['pnl'], mark['price']
            row.update(current_price=str(price), unrealized_pnl=str(pnl), mark_at=mark['at'], mark_source=mark['source'])
            unrealized_pnl += pnl
            spec = contract_from_instrument(position.instrument)
            market_value += pnl if position.instrument.instrument_type == InstrumentType.FUTURE else spec.value(price, position.quantity)
            margin += TradingOrderService.position_margin(account, position.instrument, position.quantity, position.average_price)

        reserved = sum((order.reserved_cash for order in orders), Decimal("0"))
        return {
            "account": {
                "id": account.pk, "balance": str(account.balance), "margin": str(margin),
                "reserved_cash": str(reserved),
                "available_balance": str(max(account.balance - margin - reserved, Decimal("0"))),
                "realized_pnl": str(account.realized_pnl), "unrealized_pnl": str(unrealized_pnl),
                "market_value": str(market_value), "equity": str(account.balance + market_value),
                "created_at": account.created_at.isoformat(),
                "charge_profile": account.charge_profile_id,
                "charges_paid": str(account.charges_paid),
                "futures_margin_pct": str(account.futures_margin_pct),
                "short_option_margin_pct": str(account.short_option_margin_pct),
                "starting_balance": str(account.starting_balance),
            },
            "watchlist": InstrumentSerializer(watchlist.instruments.order_by("symbol"), many=True).data,
            "watchlist_id": watchlist.pk,
            "watchlists": list(Watchlist.objects.filter(user=user).order_by('id').values('id', 'name')),
            "positions": position_data,
            "open_orders": OrderSerializer(orders, many=True).data,
        }
