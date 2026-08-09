from rest_framework import serializers

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, SlippageRecord, TradingSession
from strategies.models import StrategyVersion


class TradingSessionSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True)
    open_positions = serializers.SerializerMethodField()
    active_orders = serializers.SerializerMethodField()
    broker_session_valid = serializers.SerializerMethodField()
    allocation = serializers.SerializerMethodField()

    class Meta:
        model = TradingSession
        fields = [
            "id",
            "strategy",
            "strategy_name",
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
        return obj.strategy.live_positions.filter(user=obj.user).count()

    def get_active_orders(self, obj):
        return obj.orders.filter(status__in=["PENDING", "PLACED", "PARTIAL_FILL"]).count()

    def get_broker_session_valid(self, obj):
        latest = obj.broker_credential.sessions.filter(is_valid=True).order_by("-created_at").first() if obj.broker_credential_id else None
        return bool(latest)

    def get_allocation(self, obj):
        allocation = LiveStrategyAllocation.objects.filter(
            user=obj.user,
            strategy=obj.strategy,
            broker_credential=obj.broker_credential,
        ).first()
        if not allocation:
            return None
        return {
            "id": allocation.id,
            "allocation_type": allocation.allocation_type,
            "allocated_capital": str(allocation.allocated_capital),
            "allocated_percentage": str(allocation.allocated_percentage),
            "used_capital": str(allocation.used_capital),
            "reserved_capital": str(allocation.reserved_capital),
            "available_capital": str(allocation.available_capital),
            "realized_pnl": str(allocation.realized_pnl),
            "unrealized_pnl": str(allocation.unrealized_pnl),
            "total_pnl": str(allocation.total_pnl),
            "is_over_allocated": allocation.is_over_allocated,
            "version_id": allocation.deployed_version_id,
            "version_number": allocation.deployed_version.version_number if allocation.deployed_version else None,
            "breach_reason": allocation.breach_reason,
        }


class LiveOrderSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    instrument_symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    allocation_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LiveOrder
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "session",
            "portfolio",
            "broker_credential",
            "broker_name",
            "allocation_id",
            "broker_order_id",
            "exchange_order_id",
            "instrument",
            "instrument_symbol",
            "source_type",
            "reduce_only",
            "requested_value",
            "order_type",
            "product_type",
            "side",
            "price",
            "trigger_price",
            "quantity",
            "filled_quantity",
            "pending_quantity",
            "avg_fill_price",
            "status",
            "rejection_reason",
            "rejection_code",
            "can_cancel",
            "validity",
            "placed_at",
            "executed_at",
            "cancelled_at",
        ]
        read_only_fields = fields

    def get_can_cancel(self, obj):
        return obj.status in {"PENDING", "PLACED", "PARTIAL_FILL"}


class LivePositionSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    instrument_symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    broker_name = serializers.CharField(source="broker_credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="broker_credential.label", read_only=True)
    allocation_id = serializers.IntegerField(read_only=True)

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
            "source_type",
            "product_type",
            "side",
            "quantity",
            "avg_price",
            "current_price",
            "unrealized_pnl",
            "realized_pnl",
            "day_pnl",
            "last_broker_sync",
            "opened_at",
            "last_updated",
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

    class Meta:
        model = LiveStrategyAllocation
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "portfolio",
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
            "last_synced_at",
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
            "last_synced_at",
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

    class Meta:
        model = ExecutionLog
        fields = ["id", "order", "order_symbol", "event_type", "message", "fill_quantity", "fill_price", "latency_ms", "created_at"]
        read_only_fields = fields


class SlippageRecordSerializer(serializers.ModelSerializer):
    order_symbol = serializers.CharField(source="order.instrument.sym_ticker", read_only=True)

    class Meta:
        model = SlippageRecord
        fields = ["id", "order", "order_symbol", "expected_price", "actual_price", "slippage_pct", "slippage_amount", "market_impact", "created_at"]
        read_only_fields = fields
