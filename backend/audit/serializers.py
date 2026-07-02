from rest_framework import serializers

from .models import AuditLog, ComplianceCheck, StrategyApproval


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True, default="System")

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_name", "action", "entity_type", "entity_id",
            "entity_name", "old_value", "new_value", "ip_address",
            "user_agent", "session_id", "timestamp", "created_at", "updated_at",
        ]
        read_only_fields = fields


class StrategyApprovalSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    compliance_summary = serializers.SerializerMethodField()

    class Meta:
        model = StrategyApproval
        fields = [
            "id", "strategy", "strategy_name", "requested_by", "requested_by_name",
            "approved_by", "approved_by_name", "status", "comments",
            "requested_at", "decided_at", "compliance_summary",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "requested_by", "approved_by", "requested_at", "decided_at",
            "created_at", "updated_at",
        ]

    def get_approved_by_name(self, obj):
        return obj.approved_by.username if obj.approved_by else None

    def get_compliance_summary(self, obj):
        from .services import AuditService
        return AuditService.get_compliance_summary(obj.strategy)


class ComplianceCheckSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = ComplianceCheck
        fields = [
            "id", "strategy", "strategy_name", "check_type", "passed",
            "details", "checked_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AuditStatsSerializer(serializers.Serializer):
    """Summary statistics for the audit dashboard."""
    total_logs = serializers.IntegerField()
    today_logs = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    total_compliance_checks = serializers.IntegerField()
    compliance_pass_rate = serializers.FloatField()
    action_breakdown = serializers.DictField()
    entity_breakdown = serializers.DictField()
    recent_activity = AuditLogSerializer(many=True)
