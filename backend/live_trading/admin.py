from django.contrib import admin

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, SlippageRecord, TradingSession


@admin.register(TradingSession)
class TradingSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "status", "trades_count", "pnl", "updated_at"]
    list_filter = ["status"]


@admin.register(LiveOrder)
class LiveOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "instrument", "side", "quantity", "status", "source_type", "broker_order_id"]
    list_filter = ["status", "order_type", "product_type", "side", "source_type"]


@admin.register(LivePosition)
class LivePositionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "instrument", "side", "quantity", "avg_price", "unrealized_pnl", "source_type"]
    list_filter = ["side", "product_type", "source_type"]


@admin.register(LiveStrategyAllocation)
class LiveStrategyAllocationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "broker_credential", "allocated_capital", "used_capital", "available_capital", "is_over_allocated"]
    list_filter = ["broker_credential__broker_name", "is_active", "is_over_allocated"]


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "event_type", "fill_quantity", "fill_price", "created_at"]
    list_filter = ["event_type"]


@admin.register(SlippageRecord)
class SlippageRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "expected_price", "actual_price", "slippage_pct"]
