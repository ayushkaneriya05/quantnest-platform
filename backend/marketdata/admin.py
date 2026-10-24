# backend/marketdata/admin.py
from django.contrib import admin

from .models import Candle, MarketDataToken


@admin.register(MarketDataToken)
class MarketDataTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "is_active", "expires_at", "updated_at")


@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    """Inspect acquired data; writes belong to history ingestion and its coverage."""
    list_display = ("symbol", "timeframe", "time", "open", "high", "low", "close", "volume")
    list_filter = ("timeframe",)
    search_fields = ("symbol",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
