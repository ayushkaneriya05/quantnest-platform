"""
Serializers for the paper_trading app.
"""
from rest_framework import serializers
from .models import PaperAccount, PaperPosition, PaperOrder, PaperTrade


class PaperAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperAccount
        fields = [
            'id', 'name', 'initial_balance', 'current_balance',
            'total_pnl', 'realized_pnl', 'unrealized_pnl',
            'today_pnl', 'today_trades', 'margin_used', 'margin_available',
            'is_active', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


class PaperPositionSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    invested_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = PaperPosition
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'side', 'quantity', 'avg_price', 'current_price',
            'unrealized_pnl', 'unrealized_pnl_pct', 'realized_pnl',
            'margin_blocked', 'current_value', 'invested_value', 'opened_at'
        ]


class PaperOrderSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_filled = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaperOrder
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'order_type', 'product_type', 'side', 'quantity', 'price', 'trigger_price',
            'filled_quantity', 'avg_fill_price', 'slippage_applied',
            'status', 'rejection_reason', 'order_tag',
            'is_filled', 'is_pending', 'placed_at', 'executed_at'
        ]
        read_only_fields = ['filled_quantity', 'avg_fill_price', 'status', 'placed_at', 'executed_at']


class PaperTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_winner = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaperTrade
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'side', 'quantity', 'entry_price', 'entry_time',
            'exit_price', 'exit_time', 'exit_reason',
            'gross_pnl', 'brokerage', 'slippage', 'net_pnl', 'pnl_pct',
            'holding_duration_seconds', 'is_winner'
        ]


class PlaceOrderSerializer(serializers.Serializer):
    """Serializer for placing new orders."""
    account = serializers.IntegerField()
    instrument = serializers.IntegerField()
    strategy = serializers.IntegerField(required=False, allow_null=True)
    order_type = serializers.ChoiceField(choices=['MARKET', 'LIMIT', 'STOP_LIMIT', 'STOP_MARKET'])
    product_type = serializers.ChoiceField(choices=['CNC', 'MIS', 'NRML'], default='MIS')
    side = serializers.ChoiceField(choices=['BUY', 'SELL'])
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    trigger_price = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)
    order_tag = serializers.CharField(max_length=50, required=False, allow_blank=True)
