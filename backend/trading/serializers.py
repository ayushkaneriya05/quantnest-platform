from rest_framework import serializers
from instruments.models import Instrument

from .models import Watchlist, Account, Position, Order, TradeHistory, ClosedPositionLog
from .services import TradingOrderService

class InstrumentSerializer(serializers.ModelSerializer):
    """
    Serializes Instrument data for read operations.
    """
    company_name = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Instrument
        fields = ['id', 'symbol', 'company_name', 'exchange', 'sym_ticker']

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
        read_only_fields = ['quantity', 'average_price']

    def validate(self, attrs):
        instance = self.instance
        if instance is None:
            return attrs

        stop_loss = attrs.get("stop_loss", instance.stop_loss)
        take_profit = attrs.get("take_profit", instance.take_profit)
        average_price = instance.average_price

        if instance.quantity > 0:
            if stop_loss is not None and stop_loss >= average_price:
                raise serializers.ValidationError({"stop_loss": "Stop loss for a long position must be below average price."})
            if take_profit is not None and take_profit <= average_price:
                raise serializers.ValidationError({"take_profit": "Take profit for a long position must be above average price."})
        elif instance.quantity < 0:
            if stop_loss is not None and stop_loss <= average_price:
                raise serializers.ValidationError({"stop_loss": "Stop loss for a short position must be above average price."})
            if take_profit is not None and take_profit >= average_price:
                raise serializers.ValidationError({"take_profit": "Take profit for a short position must be below average price."})

        return attrs

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
        instrument_symbol = validated_data.get("instrument_symbol")
        transaction_type = validated_data.get("transaction_type")

        if not instrument_symbol:
            raise serializers.ValidationError({"instrument_symbol": "This field is required for creating an order."})
        if not transaction_type:
            raise serializers.ValidationError({"transaction_type": "This field is required for creating an order."})

        try:
            return TradingOrderService.create_order(self.context["request"].user, validated_data)
        except serializers.ValidationError:
            raise
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

    def validate(self, attrs):
        order_type = attrs.get("order_type", getattr(self.instance, "order_type", None))
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        price = attrs.get("price", getattr(self.instance, "price", None))
        trigger_price = attrs.get("trigger_price", getattr(self.instance, "trigger_price", None))

        payload = {
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "trigger_price": trigger_price,
        }
        try:
            TradingOrderService.validate_payload(payload)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        if order_type == "MARKET":
            attrs["price"] = None
            attrs["trigger_price"] = None
        elif order_type == "LIMIT":
            attrs["trigger_price"] = None
        elif order_type == "STOP":
            attrs["price"] = None

        return attrs

    def update(self, instance, validated_data):
        if instance.status != "OPEN":
            raise serializers.ValidationError({"detail": "Only open orders can be modified."})

        next_order_type = validated_data.get("order_type", instance.order_type)
        fill_price = None
        if next_order_type == "MARKET":
            fill_price = TradingOrderService.get_market_fill_price(instance.instrument)

        order = super().update(instance, validated_data)
        if order.order_type == "MARKET":
            order = TradingOrderService.execute_order(order, fill_price)
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

class ClosedPositionLogSerializer(serializers.ModelSerializer):
    """
    Serializes a closed position (round-trip trade) showing Realized P&L.
    """
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = ClosedPositionLog
        fields = [
            'id', 'account', 'instrument', 'side', 'quantity', 
            'entry_price', 'exit_price', 'realized_pnl', 
            'entry_time', 'exit_time'
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
