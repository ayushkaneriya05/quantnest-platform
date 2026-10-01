from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "type", "title", "message", "data",
            "is_read", "read_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["id", "type", "in_app_enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "type", "created_at", "updated_at"]
