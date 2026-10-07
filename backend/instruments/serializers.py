"""
Serializers for the instruments app.
"""
from rest_framework import serializers
from .models import Instrument, WatchlistInstrument, ExecutionRoute


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = [
            'id', 'fy_token', 'exchange_token', 'symbol', 'name',
            'sym_ticker', 'short_name', 'display_name', 'description', 'isin',
            'exchange', 'segment', 'series', 'ex_inst_type',
            'instrument_type', 'option_type', 'currency_code',
            'strike_price', 'expiry_date', 'underlying_symbol', 'underlying_fy_token',
            'lot_size', 'tick_size', 'qty_freeze', 'qty_multiplier', 'face_value',
            'circuit_limit_upper', 'circuit_limit_lower', 'trading_session',
            'previous_close', 'previous_oi',
            'is_mtf_tradable', 'mtf_margin', 'asm_gsm_flag',
            'has_options', 'has_futures', 'stream',
            'is_tradeable', 'is_active', 'last_sync_date',
        ]


class ExecutionRouteSerializer(serializers.ModelSerializer):
    def validate_watchlist_instrument(self, watch):
        request = self.context.get("request")
        if request and watch.strategy.user_id != request.user.pk:
            raise serializers.ValidationError("Select an instrument from your own strategy.")
        return watch

    def validate(self, attrs):
        override = attrs.get("override_sizing", getattr(self.instance, "override_sizing", False))
        method = attrs.get("sizing_method", getattr(self.instance, "sizing_method", None))
        quantity = attrs.get("fixed_quantity", getattr(self.instance, "fixed_quantity", None))
        percentage = attrs.get("capital_percentage", getattr(self.instance, "capital_percentage", None))
        if override:
            if method not in ("FIXED", "CAPITAL_BASED"):
                raise serializers.ValidationError({"sizing_method": "Choose fixed quantity or capital-based sizing."})
            if method == "FIXED" and (quantity is None or quantity < 1):
                raise serializers.ValidationError({"fixed_quantity": "Quantity must be at least 1."})
            if method == "CAPITAL_BASED" and (percentage is None or not 0 < percentage <= 100):
                raise serializers.ValidationError({"capital_percentage": "Capital percentage must be greater than 0 and at most 100."})
        return attrs

    class Meta:
        model = ExecutionRoute
        fields = [
            'id', 'watchlist_instrument', 'route_type', 'target_instrument',
            'target_underlying_instrument', 'expiry_preference', 'avoid_same_day_expiry',
            'buy_signal_option_type', 'sell_signal_option_type', 'strike_selection',
            'override_sizing', 'sizing_method', 'fixed_quantity', 
            'capital_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WatchlistInstrumentSerializer(serializers.ModelSerializer):
    def validate_strategy(self, strategy):
        request = self.context.get("request")
        if request and strategy.user_id != request.user.pk:
            raise serializers.ValidationError("Select one of your own strategies.")
        return strategy

    instrument_details = InstrumentSerializer(source='instrument', read_only=True)
    execution_routes = ExecutionRouteSerializer(many=True, read_only=True)

    class Meta:
        model = WatchlistInstrument
        fields = ['id', 'strategy', 'instrument', 'instrument_details', 'execution_routes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
