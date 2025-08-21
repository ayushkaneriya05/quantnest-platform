from rest_framework import serializers
from .models import Instrument, Watchlist

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['id', 'symbol', 'company_name']

class WatchlistSerializer(serializers.ModelSerializer):
    instruments = InstrumentSerializer(many=True, read_only=True)

    class Meta:
        model = Watchlist
        fields = ['id', 'user', 'instruments']
        
from .models import Account, Position, Order, TradeHistory

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'user', 'balance', 'margin']

class PositionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)
    position_type = serializers.CharField(source='get_position_type', read_only=True)
    abs_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Position
        fields = [
            'id', 'instrument', 'quantity', 'abs_quantity', 'average_price',
            'realized_pnl', 'position_type', 'created_at', 'updated_at'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['position_type'] = 'Long' if instance.is_long else 'Short'
        return data

class OrderSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(write_only=True, required=False)
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'instrument', 'instrument_symbol', 'order_type', 'status',
            'transaction_type', 'quantity', 'price', 'trigger_price',
            'created_at', 'executed_at'
        ]
        read_only_fields = ['id', 'instrument', 'created_at', 'executed_at']

    def create(self, validated_data):
        instrument_symbol = validated_data.pop('instrument_symbol', None)
        if instrument_symbol:
            try:
                instrument = Instrument.objects.get(symbol=instrument_symbol)
                validated_data['instrument'] = instrument
            except Instrument.DoesNotExist:
                raise serializers.ValidationError(
                    {"instrument_symbol": "Instrument not found"}
                )

        account = validated_data.pop('account')
        order = Order.objects.create(account=account, **validated_data)
        return order

    def validate(self, data):
        # Validate order based on transaction type
        transaction_type = data.get('transaction_type')
        order_type = data.get('order_type')

        if order_type in ['LIMIT', 'STOP_LIMIT'] and not data.get('price'):
            raise serializers.ValidationError("Price is required for limit orders")

        if order_type in ['STOP', 'STOP_LIMIT'] and not data.get('trigger_price'):
            raise serializers.ValidationError("Trigger price is required for stop orders")

        return data

class TradeHistorySerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    class Meta:
        model = TradeHistory
        fields = '__all__'
