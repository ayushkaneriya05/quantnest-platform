"""Inspect immutable settlement evidence and postings; financial writes use commands."""
from django.contrib import admin

from .models import SettlementPosting, SettlementPrice


class SettlementReadOnlyAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SettlementPrice)
class SettlementPriceAdmin(SettlementReadOnlyAdmin):
    list_display = ('instrument', 'kind', 'value', 'effective_at', 'available_at', 'source')
    list_filter = ('kind', 'instrument__exchange')
    search_fields = ('instrument__sym_ticker', 'source')
    list_select_related = ('instrument',)


@admin.register(SettlementPosting)
class SettlementPostingAdmin(SettlementReadOnlyAdmin):
    list_display = ('mode', 'account_id', 'session_id', 'route_id', 'leg_id', 'price', 'cash_change', 'created_at')
    list_filter = ('mode', 'price__kind')
    search_fields = ('identity', 'price__instrument__sym_ticker')
    list_select_related = ('price',)
