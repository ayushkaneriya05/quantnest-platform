from rest_framework import serializers

from .models import ActivityEvent, DomainEvent


class DomainEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = DomainEvent
        fields = [
            "id",
            "event_type",
            "username",
            "source_app",
            "source_model",
            "source_id",
            "idempotency_key",
            "payload",
            "status",
            "processed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ActivityEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = ActivityEvent
        fields = [
            "id",
            "username",
            "avatar",
            "activity_type",
            "title",
            "summary",
            "target_type",
            "target_id",
            "topic_slug",
            "strategy",
            "strategy_name",
            "visibility",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

