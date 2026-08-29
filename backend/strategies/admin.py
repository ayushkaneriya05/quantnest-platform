from django.contrib import admin
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig


@admin.register(StrategyTag)
class StrategyTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


class EntryOrderConfigInline(admin.StackedInline):
    model = EntryOrderConfig
    extra = 0


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'strategy_type', 'market_type', 'status', 'visibility', 'created_at']
    list_filter = ['strategy_type', 'market_type', 'status', 'visibility', 'exchange']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [EntryOrderConfigInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'name', 'description', 'tags')
        }),
        ('Classification', {
            'fields': ('strategy_type', 'market_type', 'exchange', 'instrument_type')
        }),
        ('Status', {
            'fields': ('status', 'visibility')
        }),
        ('Trading Modes', {
            'fields': ('paper_trading_enabled', 'live_trading_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StrategyVersion)
class StrategyVersionAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'version_number', 'created_by', 'created_at']
    list_filter = ['strategy']
    readonly_fields = ['created_at']
