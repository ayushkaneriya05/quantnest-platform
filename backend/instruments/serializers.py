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
    class Meta:
        model = ExecutionRoute
        fields = [
            'id', 'watchlist_instrument', 'route_type', 'target_instrument',
            'target_underlying_instrument', 'expiry_preference', 'avoid_same_day_expiry',
            'buy_signal_option_type', 'sell_signal_option_type', 'strike_selection',
            'override_sizing', 'sizing_method', 'fixed_quantity', 
            'capital_percentage', 'risk_per_trade_amount', 'risk_per_trade_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WatchlistInstrumentSerializer(serializers.ModelSerializer):
    instrument_details = InstrumentSerializer(source='instrument', read_only=True)
    execution_routes = ExecutionRouteSerializer(many=True, read_only=True)

    class Meta:
        model = WatchlistInstrument
        fields = ['id', 'strategy', 'instrument', 'instrument_details', 'execution_routes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
