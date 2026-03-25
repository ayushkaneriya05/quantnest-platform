"""
Serializers for the instruments app.
"""
from rest_framework import serializers
from .models import Instrument, WatchlistInstrument


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


class WatchlistInstrumentSerializer(serializers.ModelSerializer):
    instrument_details = InstrumentSerializer(source='instrument', read_only=True)
    
    class Meta:
        model = WatchlistInstrument
        fields = ['id', 'strategy', 'instrument', 'instrument_details', 'created_at']
