from django.contrib import admin

from .models import ExchangeConfig, MarketHoliday


class ImmutableAdmin(admin.ModelAdmin):
    """Display retained records without allowing their mutation or removal."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExchangeConfig)
class ExchangeConfigAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'segment', 'timezone', 'market_open', 'market_close', 'is_active')
    list_filter = ('exchange', 'segment', 'is_active')
    search_fields = ('exchange',)


@admin.register(MarketHoliday)
class MarketHolidayAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'date', 'description', 'is_partial', 'partial_open', 'partial_close')
    list_filter = ('exchange', 'is_partial')
    search_fields = ('description',)
    date_hierarchy = 'date'

