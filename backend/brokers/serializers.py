from rest_framework import serializers

from .models import BrokerAPILog, BrokerCredential, BrokerFundsSnapshot, BrokerSession, OrderReconciliation, OrderSettings


class BrokerCredentialSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ["client_id", "api_key", "api_secret", "totp_secret"]:
            data.pop(field, None)
        return data

    class Meta:
        model = BrokerCredential
        fields = [
            "id",
            "broker_name",
            "label",
            "client_id",
            "api_key",
            "api_secret",
            "totp_secret",
            "permissions",
            "is_active",
            "is_verified",
            "last_verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_verified", "last_verified_at", "created_at", "updated_at"]
        extra_kwargs = {
            "api_key": {"write_only": True, "required": False, "allow_blank": True},
            "api_secret": {"write_only": True, "required": False, "allow_blank": True},
            "totp_secret": {"write_only": True, "required": False, "allow_blank": True},
        }


class BrokerSessionSerializer(serializers.ModelSerializer):
    broker_name = serializers.CharField(source="credential.broker_name", read_only=True)

    class Meta:
        model = BrokerSession
        fields = [
            "id",
            "credential",
            "broker_name",
            "token_expiry",
            "is_valid",
            "last_used_at",
            "created_at",
        ]
        read_only_fields = fields


class OrderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderSettings
        fields = [
            "id",
            "default_slippage_pct",
            "order_timeout_seconds",
            "max_retries",
            "retry_delay_ms",
            "partial_fill_action",
            "use_amo_orders",
            "primary_broker",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class OrderReconciliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReconciliation
        fields = [
            "id",
            "broker_order_id",
            "internal_order_id",
            "broker_status",
            "internal_status",
            "discrepancy_type",
            "resolved",
            "resolved_at",
            "notes",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class BrokerAPILogSerializer(serializers.ModelSerializer):
    broker_name = serializers.CharField(source="credential.broker_name", read_only=True)

    class Meta:
        model = BrokerAPILog
        fields = [
            "id",
            "broker_name",
            "endpoint",
            "request_data",
            "response_data",
            "status_code",
            "latency_ms",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class BrokerFundsSnapshotSerializer(serializers.ModelSerializer):
    broker_name = serializers.CharField(source="credential.broker_name", read_only=True)
    broker_label = serializers.CharField(source="credential.label", read_only=True)

    class Meta:
        model = BrokerFundsSnapshot
        fields = [
            "id",
            "credential",
            "broker_name",
            "broker_label",
            "cash_balance",
            "available_margin",
            "used_margin",
            "collateral",
            "withdrawable_balance",
            "net_equity",
            "realized_pnl",
            "unrealized_pnl",
            "raw_payload",
            "snapshot_time",
            "created_at",
        ]
        read_only_fields = fields
