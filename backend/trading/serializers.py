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
    class Meta:
        model = Position
        fields = ['id', 'instrument', 'quantity', 'average_price']

class OrderSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(write_only=True)
    class Meta:
        model = Order
        fields = [
            'id', 'instrument', 'instrument_symbol', 'order_type', 'status', 
            'transaction_type', 'quantity', 'price', 'trigger_price', 'created_at'
        ]
        read_only_fields = ['id', 'instrument', 'status', 'created_at']

    def create(self, validated_data):
        instrument_symbol = validated_data.pop('instrument_symbol')
        instrument = Instrument.objects.get(symbol=instrument_symbol)
        account, _ = Account.objects.get_or_create(user=self.context['request'].user)
        order = Order.objects.create(account=account, instrument=instrument, **validated_data)
        return order

class TradeHistorySerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    class Meta:
        model = TradeHistory
        fields = '__all__'