from rest_framework import serializers

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession
from strategies.serializers import StrategyVersionListSerializer


class TradingSessionSerializer(serializers.ModelSerializer):
    applied_version = serializers.IntegerField(source='applied_version_id', read_only=True, allow_null=True)
    applied_at = serializers.DateTimeField(read_only=True)
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    strategy_status = serializers.CharField(source="strategy.status", read_only=True)
    live_trading_enabled = serializers.BooleanField(source="strategy.live_trading_enabled", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True)
    open_positions = serializers.IntegerField(source="allocation.annotated_open_positions", default=0, read_only=True)
    active_orders = serializers.IntegerField(source="annotated_active_orders", read_only=True)
    broker_session_valid = serializers.BooleanField(source="annotated_broker_session_valid", read_only=True)
    allocation = serializers.SerializerMethodField()
    trades_count = serializers.IntegerField(source="allocation.annotated_trade_count", read_only=True, default=0)
    pnl = serializers.DecimalField(source="allocation.annotated_total_pnl", max_digits=18, decimal_places=4, read_only=True, default=0)

    class Meta:
        model = TradingSession
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "strategy_status",
            "live_trading_enabled",
            "broker_credential",
            "broker_name",
            "broker_label",
            "started_at",
            "ended_at",
            "status",
            "trades_count",
            "pnl",
            "error_message",
            "open_positions",
            "active_orders",
            "broker_session_valid",
            "allocation",
            "applied_version",
            "applied_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["started_at", "ended_at", "trades_count", "pnl", "error_message", "created_at", "updated_at"]

    def get_allocation(self, obj):
        allocation = obj.allocation
        if not allocation:
            return None
        return {
            "id": allocation.id,
            "allocated_capital": str(allocation.allocated_capital),
            "used_capital": str(allocation.annotated_used_capital),
            "reserved_capital": str(allocation.annotated_reserved_capital),
            "available_capital": str(allocation.annotated_available_capital),
            "realized_pnl": str(allocation.annotated_realized_pnl),
            "unrealized_pnl": str(allocation.annotated_unrealized_pnl),
            "total_pnl": str(allocation.annotated_total_pnl),
            "is_over_allocated": allocation.is_over_allocated,
            "version_id": allocation.deployed_version_id,
            "version_number": allocation.deployed_version.version_number if allocation.deployed_version else None,
            "breach_reason": allocation.breach_reason,
        }


class LiveOrderSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    instrument_symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True, allow_null=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True, allow_null=True)
    allocation_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LiveOrder
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "session",
            "broker_credential",
            "broker_name",
            "broker_label",
            "allocation_id",
            "broker_order_id",
            "exchange_order_id",
            "instrument",
            "instrument_symbol",
            "order_type",
            "product_type",
            "side",
            "price",
            "quantity",
            "filled_quantity",
            "pending_quantity",
            "avg_fill_price",
            "status",
            "rejection_reason",
            "placed_at",
            "broker_ordered_at",
            "broker_updated_at",
            "executed_at",
            "cancelled_at",
        ]
        read_only_fields = fields

class LivePositionSerializer(serializers.ModelSerializer):
    mark_at = serializers.DateTimeField(source="last_updated", read_only=True)
    qty_multiplier = serializers.DecimalField(source='instrument.qty_multiplier', max_digits=10, decimal_places=4, read_only=True)
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    instrument_symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True, allow_null=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True, allow_null=True)
    allocation_id = serializers.IntegerField(read_only=True)
    return_percent = serializers.SerializerMethodField()

    class Meta:
        model = LivePosition
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "broker_credential",
            "broker_name",
            "broker_label",
            "allocation_id",
            "instrument",
            "instrument_symbol",
            "product_type",
            "side",
            "quantity", 'qty_multiplier',
            "avg_price",
            "current_price",
            "mark_at",
            "unrealized_pnl",
            "return_percent",
            "opened_at",
            "last_updated",
        ]
        read_only_fields = fields

    def get_return_percent(self, obj):
        entry_value = obj.avg_price * obj.quantity * obj.instrument.qty_multiplier
        if not entry_value:
            return 0
        return round(float(obj.unrealized_pnl / entry_value * 100), 4)


class LiveTradeSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    instrument_symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True, allow_null=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True, allow_null=True)

    class Meta:
        model = LiveTrade
        fields = [
            "id", "strategy", "strategy_name", "allocation", "broker_credential",
            "broker_name", "broker_label", "instrument", "instrument_symbol",
            "exit_order", "side", "quantity", "entry_price", "entry_time",
            "exit_price", "exit_time", "exit_reason", "gross_pnl", "realized_pnl",
            "holding_duration_seconds",
        ]
        read_only_fields = fields


class LiveStrategyAllocationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True)
    deployed_version = serializers.IntegerField(source="deployed_version_id", read_only=True, allow_null=True)
    deployed_version_detail = StrategyVersionListSerializer(source='deployed_version', read_only=True)
    used_capital = serializers.ReadOnlyField(source="annotated_used_capital")
    reserved_capital = serializers.ReadOnlyField(source="annotated_reserved_capital")
    available_capital = serializers.ReadOnlyField(source="annotated_available_capital")
    realized_pnl = serializers.ReadOnlyField(source="annotated_realized_pnl")
    unrealized_pnl = serializers.ReadOnlyField(source="annotated_unrealized_pnl")
    total_pnl = serializers.ReadOnlyField(source="annotated_total_pnl")

    class Meta:
        model = LiveStrategyAllocation
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "broker_credential",
            "broker_name",
            "broker_label",
            "allocated_capital",
            "used_capital",
            "reserved_capital",
            "available_capital",
            "realized_pnl",
            "unrealized_pnl",
            "total_pnl",
            "broker_equity_reference",
            "is_over_allocated",
            "breach_reason",
            "created_at",
            "updated_at",
            "deployed_version",
            "deployed_version_detail"
        ]
        read_only_fields = [
            "used_capital",
            "reserved_capital",
            "available_capital",
            "realized_pnl",
            "unrealized_pnl",
            "total_pnl",
            "broker_equity_reference",
            "is_over_allocated",
            "breach_reason",
            "created_at",
            "updated_at",
        ]

class ExecutionLogSerializer(serializers.ModelSerializer):
    order_symbol = serializers.CharField(source="order.instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="order.broker_credential.broker_name", read_only=True, allow_null=True)
    broker_label = serializers.CharField(source="order.broker_credential.label", read_only=True, allow_null=True)

    class Meta:
        model = ExecutionLog
        fields = ["id", "order", "order_symbol", "broker_name", "broker_label", "event_type", "message", "latency_ms", "created_at"]
        read_only_fields = fields


class SlippageRecordSerializer(serializers.ModelSerializer):
    order_symbol = serializers.CharField(source="order.instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="order.broker_credential.broker_name", read_only=True, allow_null=True)
    broker_label = serializers.CharField(source="order.broker_credential.label", read_only=True, allow_null=True)

    class Meta:
        model = SlippageRecord
        fields = ["id", "order", "order_symbol", "broker_name", "broker_label", "expected_price", "actual_price", "slippage_pct", "slippage_amount", "market_impact", "created_at"]
        read_only_fields = fields
