from django.contrib import admin
from .models import Instrument, ContractSpecification


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['sym_ticker', 'symbol', 'name', 'exchange', 'segment', 'instrument_type', 'is_tradeable', 'is_active']
    list_filter = ['exchange', 'segment', 'instrument_type', 'is_active', 'is_tradeable', 'has_options', 'has_futures']
    search_fields = ['symbol', 'name', 'sym_ticker', 'fy_token']
    ordering = ['symbol']


@admin.register(ContractSpecification)
class ContractSpecificationAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'effective_at', 'lot_size', 'tick_size', 'qty_multiplier', 'source']
    search_fields = ['instrument__sym_ticker', 'instrument__name', 'source']
    autocomplete_fields = ['instrument']
    readonly_fields = ['recorded_at']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
