from rest_framework import serializers

from .models import DailySummarySchedule, Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "type",
            "severity",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["read_at", "created_at", "updated_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "notification_type",
            "in_app_enabled",
            "email_enabled",
            "sms_enabled",
            "telegram_enabled",
            "telegram_chat_id",
            "push_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class DailySummaryScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySummarySchedule
        fields = ["id", "is_enabled", "send_time", "include_pnl", "include_trades", "include_insights", "last_sent_at", "updated_at"]
        read_only_fields = ["last_sent_at", "updated_at"]

