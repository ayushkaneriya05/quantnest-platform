from django.contrib import admin
from .models import PaperAccount, PaperPosition, PaperOrder, PaperTrade, Portfolio

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'initial_capital', 'current_capital', 'created_at', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PaperAccount)
class PaperAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'initial_balance', 'current_balance', 'total_pnl', 'today_pnl']
    search_fields = ['name', 'user__username']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PaperPosition)
class PaperPositionAdmin(admin.ModelAdmin):
    list_display = ['account', 'instrument', 'side', 'quantity', 'avg_price', 'current_price', 'unrealized_pnl']
    list_filter = ['side', 'account']
    search_fields = ['instrument__symbol']


@admin.register(PaperOrder)
class PaperOrderAdmin(admin.ModelAdmin):
    list_display = ['account', 'instrument', 'order_type', 'side', 'quantity', 'price', 'status', 'placed_at']
    list_filter = ['order_type', 'side', 'status', 'product_type']
    search_fields = ['instrument__symbol', 'order_tag']
    readonly_fields = ['placed_at', 'executed_at']


@admin.register(PaperTrade)
class PaperTradeAdmin(admin.ModelAdmin):
    list_display = ['account', 'instrument', 'side', 'quantity', 'entry_price', 'exit_price', 'net_pnl', 'pnl_pct']
    list_filter = ['side', 'exit_reason']
    search_fields = ['instrument__symbol']
    readonly_fields = ['created_at', 'updated_at']
