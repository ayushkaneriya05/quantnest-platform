"""Typed Terminal API contracts. Trading mutations belong to the account service."""
from common.enums import (
    InstrumentType, ExchangeInstrumentType, TerminalOrderType, TerminalOrderStatus,
    Side, TERMINAL_USER_ORDER_TYPES,
)
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from brokers.models import BrokerChargeProfile
from .models import Watchlist, Account, Position, Order, TradeHistory, ClosedPositionLog
from .services import TradingOrderService


class InstrumentSerializer(serializers.ModelSerializer):
    orderable = serializers.SerializerMethodField()

    class Meta:
        from instruments.models import Instrument
        model = Instrument
        fields = ['id', 'symbol', 'name', 'exchange', 'segment', 'sym_ticker',
                  'instrument_type', 'option_type', 'strike_price', 'expiry_date',
                  'underlying_symbol', 'lot_size', 'qty_multiplier', 'tick_size',
                  'qty_freeze', 'currency_code', 'orderable']

    def get_orderable(self, obj):
        return obj.is_active and obj.is_tradeable and obj.instrument_type not in (InstrumentType.INDEX, InstrumentType.MF) and obj.ex_inst_type != ExchangeInstrumentType.UNDCUR and (not obj.expiry_date or obj.expiry_date >= timezone.localdate())


class WatchlistSerializer(serializers.ModelSerializer):
    instruments = InstrumentSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'name', 'instruments']

    def validate_name(self, value):
        lists = Watchlist.objects.filter(user=self.context['request'].user, name=value)
        if self.instance:
            lists = lists.exclude(pk=self.instance.pk)
        if lists.exists():
            raise serializers.ValidationError('Choose a different watchlist name.')
        return value


class AccountSerializer(serializers.ModelSerializer):
    charge_profile = serializers.PrimaryKeyRelatedField(queryset=BrokerChargeProfile.objects.none(), allow_null=True, required=False)
    futures_margin_pct = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=1, max_value=100)
    short_option_margin_pct = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=1, max_value=100)

    class Meta:
        model = Account
        fields = ['id', 'user', 'balance', 'margin', 'realized_pnl', 'unrealized_pnl',
                  'created_at', 'charge_profile', 'charges_paid', 'starting_balance',
                  'futures_margin_pct', 'short_option_margin_pct']
        read_only_fields = ['id', 'user', 'balance', 'margin', 'realized_pnl', 'unrealized_pnl',
                            'created_at', 'charges_paid', 'starting_balance']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            self.fields['charge_profile'].queryset = BrokerChargeProfile.objects.filter(user=request.user)

    @transaction.atomic
    def update(self, instance, data):
        from common.enums import ExecutionMode, ExecutionCommandType
        from execution.repository import enqueue
        account = Account.objects.select_for_update().get(pk=instance.pk)
        if any(key in data and data[key] != getattr(account, key)
               for key in ('futures_margin_pct', 'short_option_margin_pct')):
            if Order.objects.filter(account=account, status=TerminalOrderStatus.OPEN).exists():
                raise serializers.ValidationError('Finish working orders before changing margin settings.')
        changes = {key: value.pk if key == 'charge_profile' and value else value for key, value in data.items()}
        enqueue(ExecutionMode.TERMINAL, account.pk, ExecutionCommandType.REFRESH, {'terminal_changes': changes})
        return account


class PositionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Position
        fields = ['id', 'instrument', 'quantity', 'average_price', 'stop_loss', 'take_profit']
        read_only_fields = ['quantity', 'average_price']

    @transaction.atomic
    def update(self, instance, data):
        from common.enums import ExecutionMode, ExecutionCommandType
        from execution.repository import enqueue
        position = Position.objects.select_for_update().get(pk=instance.pk)
        enqueue(ExecutionMode.TERMINAL, position.account_id, ExecutionCommandType.PROTECT, {
            'instrument_id': position.instrument_id,
            'unit': [ExecutionMode.TERMINAL, position.account_id, position.instrument_id],
            'stop': data.get('stop_loss', position.stop_loss),
            'target': data.get('take_profit', position.take_profit),
        })
        return position


class OrderSerializer(serializers.ModelSerializer):
    order_type = serializers.ChoiceField(choices=TERMINAL_USER_ORDER_TYPES, required=False)
    instrument = InstrumentSerializer(read_only=True)
    sym_ticker = serializers.SlugRelatedField(source='instrument', slug_field='sym_ticker', queryset=InstrumentSerializer.Meta.model.objects.all(), write_only=True, required=False)
    transaction_type = serializers.ChoiceField(choices=Side.choices, required=False)

    class Meta:
        model = Order
        fields = ['id', 'instrument', 'sym_ticker', 'order_type', 'status', 'transaction_type',
                  'quantity', 'price', 'trigger_price', 'created_at', 'executed_at', 'activated_at',
                  'filled_quantity', 'avg_fill_price', 'rejection_reason',
                  'reduce_only', 'stop_loss', 'take_profit']
        read_only_fields = ['id', 'instrument', 'status', 'created_at', 'executed_at', 'activated_at',
                            'filled_quantity', 'avg_fill_price', 'rejection_reason']

    def validate(self, attrs):
        instance = self.instance
        kind = attrs.get('order_type', instance.order_type if instance else None)
        payload = {key: attrs.get(key, getattr(instance, key, None)) for key in ('quantity', 'price', 'trigger_price')}
        payload['order_type'] = kind
        try:
            TradingOrderService.validate_payload(payload)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None
        if kind == TerminalOrderType.MARKET:
            attrs.update(price=None, trigger_price=None)
        elif kind == TerminalOrderType.LIMIT:
            attrs['trigger_price'] = None
        elif kind == TerminalOrderType.STOP:
            attrs['price'] = None
        if instance and ('instrument' in attrs or 'transaction_type' in attrs or 'reduce_only' in attrs):
            raise serializers.ValidationError('Instrument, side and reduce-only mode cannot be changed.')
        if not instance and (not attrs.get('instrument') or not attrs.get('transaction_type')):
            raise serializers.ValidationError('Instrument and side are required.')
        return attrs

    def create(self, data):
        try:
            return TradingOrderService.create_order(self.context['request'].user, data)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from None

    @transaction.atomic
    def update(self, instance, data):
        from common.enums import ExecutionMode, ExecutionCommandType
        from execution.repository import enqueue
        order = Order.objects.select_for_update().get(pk=instance.pk)
        if order.status != TerminalOrderStatus.OPEN:
            raise serializers.ValidationError('Only working orders can be modified.')
        changes = {('trigger' if key == 'trigger_price' else key): value for key, value in data.items()}
        enqueue(ExecutionMode.TERMINAL, order.account_id, ExecutionCommandType.AMEND,
            {'identity': str(order.request_id), 'instrument_id': order.instrument_id, 'changes': changes})
        return order


class TradeHistorySerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(source='order.instrument', read_only=True)
    order_type = serializers.CharField(source='order.order_type', read_only=True)
    transaction_type = serializers.CharField(source='order.transaction_type', read_only=True)

    class Meta:
        model = TradeHistory
        fields = ['id', 'order', 'instrument', 'order_type', 'transaction_type', 'executed_price',
                  'quantity', 'timestamp', 'charges', 'charges_breakdown']
        read_only_fields = fields


class ClosedPositionLogSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = ClosedPositionLog
        fields = ['id', 'account', 'instrument', 'side', 'quantity', 'entry_price', 'exit_price',
                  'realized_pnl', 'gross_pnl', 'recorded_charges', 'entry_time', 'exit_time', 'exit_reason']
        read_only_fields = fields
