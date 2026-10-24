from rest_framework import serializers

from .models import BrokerAPILog, BrokerChargeProfile, BrokerCredential, BrokerFundsSnapshot, BrokerSession


class BrokerCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerCredential
        fields = [
            "id", "broker_name", "label", "client_id", "permissions",
            "is_active", "is_verified", "last_verified_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class BrokerConfigurationSerializer(serializers.Serializer):
    broker_name = serializers.CharField(max_length=20)

    def validate(self, attrs):
        from .services import BROKER_ADAPTERS
        adapter_class = BROKER_ADAPTERS.get(attrs["broker_name"])
        if adapter_class is None:
            raise serializers.ValidationError({"broker_name": "This broker is not supported yet."})
        configuration = adapter_class.configuration_serializer(data=self.initial_data)
        configuration.is_valid(raise_exception=True)
        return {**attrs, **configuration.validated_data}


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


class BrokerChargeProfileSerializer(serializers.ModelSerializer):
    """Serializer for BrokerChargeProfile CRUD operations."""

    class Meta:
        model = BrokerChargeProfile
        fields = [
            'id', 'name',
            'brokerage_per_order', 'brokerage_pct', 'brokerage_cap',
            'stt_eq_delivery_pct', 'stt_eq_intraday_pct',
            'stt_futures_pct', 'stt_options_sell_pct',
            'ctt_futures_sell_pct', 'ctt_options_sell_pct',
            'exchange_txn_pct', 'exchange_txn_fo_pct',
            'sebi_turnover_pct', 'stamp_duty_pct', 'gst_pct',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_default', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Ensure unique name per user."""
        user = self.context['request'].user
        qs = BrokerChargeProfile.objects.filter(user=user, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A charge profile with this name already exists.')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
