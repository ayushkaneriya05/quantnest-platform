from rest_framework import serializers
from .models import Instrument, Watchlist, Account, Position, Order, TradeHistory
from django.shortcuts import get_object_or_404

class InstrumentSerializer(serializers.ModelSerializer):
    """
    Serializes Instrument data for read operations.
    """
    class Meta:
        model = Instrument
        fields = ['id', 'symbol', 'company_name']

class WatchlistSerializer(serializers.ModelSerializer):
    """
    Serializes the user's watchlist, nesting the instrument details.
    """
    instruments = InstrumentSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'user', 'instruments']
        
class AccountSerializer(serializers.ModelSerializer):
    """
    Serializes the user's trading account, including all P&L fields.
    """
    class Meta:
        model = Account
        fields = [
            'id', 'user', 'balance', 'margin', 
            'realized_pnl', 'unrealized_pnl', 'created_at'
        ]
        read_only_fields = ['user', 'created_at', 'realized_pnl', 'unrealized_pnl']

class PositionSerializer(serializers.ModelSerializer):
    """
    Serializes an open position, including risk management fields.
    """
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Position
        fields = [
            'id', 'instrument', 'quantity', 'average_price', 
            'stop_loss', 'take_profit'
        ]

class OrderSerializer(serializers.ModelSerializer):
    """
    Handles both creating and displaying orders.
    """
    instrument = InstrumentSerializer(read_only=True)
    instrument_symbol = serializers.CharField(write_only=True, required=False)
    transaction_type = serializers.ChoiceField(choices=Order.TRANSACTION_TYPES, required=False)

    class Meta:
        model = Order
        fields = [
            'id', 'instrument', 'instrument_symbol', 'order_type', 'status', 
            'transaction_type', 'quantity', 'price', 'trigger_price', 
            'created_at', 'executed_at'
        ]
        read_only_fields = ['id', 'instrument', 'status', 'created_at', 'executed_at']

    def create(self, validated_data):
        instrument_symbol = validated_data.pop('instrument_symbol', None)
        transaction_type = validated_data.get('transaction_type', None)

        if not instrument_symbol:
            raise serializers.ValidationError({"instrument_symbol": "This field is required for creating an order."})
        if not transaction_type:
            raise serializers.ValidationError({"transaction_type": "This field is required for creating an order."})
        
        instrument = get_object_or_404(Instrument, symbol=instrument_symbol)
        account, _ = Account.objects.get_or_create(user=self.context['request'].user)
        
        order = Order.objects.create(
            account=account, 
            instrument=instrument, 
            **validated_data
        )
        return order

class TradeHistorySerializer(serializers.ModelSerializer):
    """
    Serializes a single trade, nesting key details for context.
    """
    instrument = InstrumentSerializer(source='order.instrument', read_only=True)
    order_type = serializers.CharField(source='order.order_type', read_only=True)
    transaction_type = serializers.CharField(source='order.transaction_type', read_only=True)

    class Meta:
        model = TradeHistory
        fields = [
            'id', 'order', 'instrument', 'order_type', 'transaction_type',
            'executed_price', 'quantity', 'timestamp'
        ]
        read_only_fields = fields

class AccountSummarySerializer(serializers.ModelSerializer):
    """
    Serializes comprehensive data for the account summary page, including
    trade history and positions for frontend calculations.
    """
    positions = PositionSerializer(many=True, read_only=True)
    history = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'user', 'balance', 'margin',
            'realized_pnl', 'unrealized_pnl', 'created_at',
            'positions', 'history'
        ]

    def get_history(self, obj):
        trade_history = TradeHistory.objects.filter(order__account=obj).order_by('-timestamp')
        return TradeHistorySerializer(trade_history, many=True).data