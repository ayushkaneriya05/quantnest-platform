from django.contrib import admin
from .models import (
    Portfolio, CapitalAllocation, FundTransaction,
    ExposureSnapshot, DailyPerformance
)


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'initial_capital', 'current_capital', 'invested_value', 'today_pnl', 'is_active']
    list_filter = ['is_active', 'broker_synced']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CapitalAllocation)
class CapitalAllocationAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'allocation_type', 'allocated_amount', 'utilized_amount', 'is_active']
    list_filter = ['allocation_type', 'is_active', 'auto_rebalance']


@admin.register(FundTransaction)
class FundTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'portfolio', 'amount', 'balance_after', 'is_approved', 'created_at']
    list_filter = ['transaction_type', 'is_approved', 'requires_approval']
    search_fields = ['notes']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ExposureSnapshot)
class ExposureSnapshotAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'snapshot_time', 'total_exposure', 'exposure_percentage', 'open_positions_count']
    list_filter = ['portfolio']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DailyPerformance)
class DailyPerformanceAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'date', 'opening_capital', 'closing_capital', 'total_pnl', 'trades_count']
    list_filter = ['portfolio', 'date']
    ordering = ['-date']
