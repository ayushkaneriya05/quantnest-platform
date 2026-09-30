from rest_framework import serializers
from django.utils import timezone

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession
from strategies.models import StrategyVersion


class TradingSessionSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    strategy_status = serializers.CharField(source="strategy.status", read_only=True)
    live_trading_enabled = serializers.BooleanField(source="strategy.live_trading_enabled", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True)
    open_positions = serializers.SerializerMethodField()
    active_orders = serializers.SerializerMethodField()
    broker_session_valid = serializers.SerializerMethodField()
    allocation = serializers.SerializerMethodField()
    trades_count = serializers.SerializerMethodField()
    pnl = serializers.SerializerMethodField()

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["started_at", "ended_at", "trades_count", "pnl", "error_message", "created_at", "updated_at"]

    def get_open_positions(self, obj):
        if hasattr(obj, "annotated_open_positions"):
            return obj.annotated_open_positions
        positions = LivePosition.objects.filter(user=obj.user, strategy_id=obj.strategy_id, quantity__gt=0)
        if obj.allocation_id:
            positions = positions.filter(allocation_id=obj.allocation_id)
        else:
            positions = positions.filter(broker_credential_id=obj.broker_credential_id)
        return positions.count()

    def get_active_orders(self, obj):
        if hasattr(obj, "annotated_active_orders"):
            return obj.annotated_active_orders
        return obj.orders.filter(status__in=["PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"]).count()

    def get_broker_session_valid(self, obj):
        if hasattr(obj, "annotated_broker_session_valid"):
            return obj.annotated_broker_session_valid
        latest = obj.broker_credential.sessions.filter(
            is_valid=True, token_expiry__gt=timezone.now()
        ).order_by("-created_at").first() if obj.broker_credential_id else None
        return bool(latest)

    def get_trades_count(self, obj):
        allocation = self._get_allocation(obj)
        if allocation is not None and hasattr(allocation, "annotated_trade_count"):
            return allocation.annotated_trade_count
        if allocation is None:
            return 0
        return obj.trades_count

    def get_pnl(self, obj):
        allocation = self._get_allocation(obj)
        if allocation is not None and hasattr(allocation, "annotated_total_pnl"):
            return allocation.annotated_total_pnl
        if allocation is None:
            return 0
        return obj.pnl

    @staticmethod
    def _get_allocation(obj):
        if hasattr(obj, "prefetched_allocation"):
            return obj.prefetched_allocation
        return obj.allocation

    def get_allocation(self, obj):
        allocation = self._get_allocation(obj)
        if not allocation:
            return None
        def value(annotation, property_name):
            return getattr(allocation, annotation) if hasattr(allocation, annotation) else getattr(allocation, property_name)

        used_capital = value("annotated_used_capital", "invested_value")
        reserved_capital = value("annotated_reserved_capital", "reserved_capital")
        realized_pnl = value("annotated_realized_pnl", "realized_pnl")
        unrealized_pnl = value("annotated_unrealized_pnl", "unrealized_pnl")
        total_pnl = value("annotated_total_pnl", "total_pnl")
        available_capital = value("annotated_available_capital", "available_capital")
        return {
            "id": allocation.id,
            "allocation_type": allocation.allocation_type,
            "allocated_capital": str(allocation.allocated_capital),
            "allocated_percentage": str(allocation.allocated_percentage),
            "used_capital": str(used_capital),
            "reserved_capital": str(reserved_capital),
            "available_capital": str(available_capital),
            "realized_pnl": str(realized_pnl),
            "unrealized_pnl": str(unrealized_pnl),
            "total_pnl": str(total_pnl),
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
            "executed_at",
            "cancelled_at",
        ]
        read_only_fields = fields

class LivePositionSerializer(serializers.ModelSerializer):
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
            "quantity",
            "avg_price",
            "current_price",
            "unrealized_pnl",
            "return_percent",
            "last_broker_sync",
            "opened_at",
            "last_updated",
        ]
        read_only_fields = fields

    def get_return_percent(self, obj):
        entry_value = obj.avg_price * obj.quantity
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
    deployed_version = serializers.PrimaryKeyRelatedField(
        queryset=StrategyVersion.objects.all(),
        required=False,
        allow_null=True,
        help_text='Pinned strategy version ID'
    )
    deployed_version_detail = serializers.SerializerMethodField()
    used_capital = serializers.ReadOnlyField(source="invested_value")
    reserved_capital = serializers.ReadOnlyField()
    available_capital = serializers.ReadOnlyField()
    realized_pnl = serializers.ReadOnlyField()
    unrealized_pnl = serializers.ReadOnlyField()
    total_pnl = serializers.ReadOnlyField()

    class Meta:
        model = LiveStrategyAllocation
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "broker_credential",
            "broker_name",
            "broker_label",
            "allocation_type",
            "allocated_capital",
            "allocated_percentage",
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

    def get_deployed_version_detail(self, obj):
        if obj.deployed_version:
            return {
                'id': obj.deployed_version.id,
                'version_number': obj.deployed_version.version_number,
                'change_notes': obj.deployed_version.change_notes,
                'created_at': obj.deployed_version.created_at.isoformat(),
            }
        return None


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
