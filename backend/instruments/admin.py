from django.contrib import admin
from .models import Instrument, WatchlistInstrument, ExecutionRoute


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['sym_ticker', 'symbol', 'name', 'exchange', 'segment', 'instrument_type', 'is_tradeable', 'is_active']
    list_filter = ['exchange', 'segment', 'instrument_type', 'is_active', 'is_tradeable', 'has_options', 'has_futures']
    search_fields = ['symbol', 'name', 'sym_ticker', 'fy_token']
    ordering = ['symbol']


@admin.register(WatchlistInstrument)
class WatchlistInstrumentAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'instrument', 'created_at']
    list_filter = ['strategy']
    autocomplete_fields = ['instrument', 'strategy']
    search_fields = ['instrument__sym_ticker', 'strategy__name']

@admin.register(ExecutionRoute)
class ExecutionRouteAdmin(admin.ModelAdmin):
    list_display = ['watchlist_instrument','target_instrument', 'target_underlying_instrument', 'route_type', 'created_at']
    list_filter = ['route_type']
    autocomplete_fields = ['watchlist_instrument', 'target_instrument', 'target_underlying_instrument']
