from django.contrib import admin

from .models import ExchangeConfig, MarketHoliday


@admin.register(ExchangeConfig)
class ExchangeConfigAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'market_open', 'market_close', 'pre_market_open', 'pre_market_close', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('exchange',)


@admin.register(MarketHoliday)
class MarketHolidayAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'date', 'description', 'is_partial', 'partial_close')
    list_filter = ('exchange', 'is_partial')
    search_fields = ('description',)
    date_hierarchy = 'date'
