from django.contrib import admin

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession


@admin.register(TradingSession)
class TradingSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "status", "updated_at"]
    list_filter = ["status"]


@admin.register(LiveOrder)
class LiveOrderAdmin(admin.ModelAdmin):
    raw_id_fields = ["instrument"]
    list_select_related = ["instrument"]
    list_display = ["id", "user", "strategy", "instrument", "side", "quantity", "status", "broker_order_id"]
    list_filter = ["status", "order_type", "product_type", "side"]


@admin.register(LivePosition)
class LivePositionAdmin(admin.ModelAdmin):
    raw_id_fields = ["instrument"]
    list_select_related = ["instrument"]
    list_display = ["id", "user", "strategy", "instrument", "side", "quantity", "avg_price", "unrealized_pnl"]
    list_filter = ["side", "product_type"]

@admin.register(LiveTrade)
class LiveTradeAdmin(admin.ModelAdmin):
    raw_id_fields = ["instrument", "exit_order"]
    list_select_related = ["instrument", "exit_order"]
    list_display = ["id", "user", "strategy", "instrument", "side", "quantity", "entry_price", "exit_price"]
    list_filter = ["side"]

@admin.register(LiveStrategyAllocation)
class LiveStrategyAllocationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "broker_credential", "allocated_capital", "is_over_allocated"]
    list_filter = ["broker_credential__broker_name", "is_over_allocated"]


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "event_type", "created_at"]
    list_filter = ["event_type"]


@admin.register(SlippageRecord)
class SlippageRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "expected_price", "actual_price", "slippage_pct"]
