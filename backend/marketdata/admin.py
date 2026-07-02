# backend/marketdata/admin.py
from django.contrib import admin

from .models import Candle, MarketDataToken, MarketEvent


@admin.register(MarketDataToken)
class MarketDataTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "is_active", "expires_at", "updated_at")


@admin.register(MarketEvent)
class MarketEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "event_date", "instrument", "impact", "source")
    list_filter = ("event_type", "impact", "event_date")
    search_fields = ("title", "description", "instrument__symbol", "instrument__name")


@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ("symbol", "timeframe", "time", "open", "high", "low", "close", "volume")
    list_filter = ("timeframe",)
    search_fields = ("symbol",)
