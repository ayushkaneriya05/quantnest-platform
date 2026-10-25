from rest_framework import serializers

from .models import ResearchAction, ResearchRun, ResearchSession


class ResearchActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchAction
        fields = ["id", "run", "action_type", "payload", "status", "resource_ids", "error_message"]
        read_only_fields = fields


class ResearchRunSerializer(serializers.ModelSerializer):
    actions = ResearchActionSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchRun
        fields = [
            "id",
            "session",
            "request_id",
            "mode",
            "prompt",
            "request",
            "status",
            "progress_message",
            "evidence",
            "result",
            "usage",
            "error_message",
            "as_of",
            "started_at",
            "completed_at",
            "created_strategy",
            "created_at",
            "revision",
            "actions",
        ]
        read_only_fields = fields


class ResearchContextSerializer(serializers.Serializer):
    """Shared attachment inputs for saved conversations and new research requests."""

    strategy_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    backtest_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    instrument_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    screen = serializers.JSONField(required=False)
    timeframe = serializers.CharField(required=False)
    watchlist_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    source_run_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    execution_review = serializers.JSONField(required=False, allow_null=True)

    def validate_execution_review(self, value):
        if value is None:
            return None
        from analytics.services import ExecutionReviewSerializer

        serializer = ExecutionReviewSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        from .validation import json_data

        return json_data(serializer.validated_data)


class ResearchSessionSerializer(serializers.ModelSerializer):
    def validate_context(self, value):
        from .context import CONTEXT_FIELDS, SAVED_CONTEXT_FIELDS, resolve_context

        allowed = set(CONTEXT_FIELDS)
        if not isinstance(value, dict) or set(value) - allowed:
            raise serializers.ValidationError("Unsupported conversation settings.")
        validated = ResearchContextSerializer(data=value)
        validated.is_valid(raise_exception=True)
        resolved = resolve_context(self.context["request"].user, validated.validated_data)
        if value.get("screen"):
            from .validation import screen_configuration

            screen_configuration(value["screen"])
        return {key: resolved[key] for key in SAVED_CONTEXT_FIELDS if key in resolved}

    class Meta:
        model = ResearchSession
        fields = ["id", "title", "context", "kind", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RunRequestSerializer(ResearchContextSerializer):
    session = serializers.IntegerField(required=False, min_value=1)
    request_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["RESEARCH", "SCREEN"], default="RESEARCH")
    prompt = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    refresh = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError("Unsupported research request fields.")
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs["mode"] == "RESEARCH" and not attrs.get("prompt"):
            raise serializers.ValidationError({"prompt": "Describe the research you want to perform."})
        if attrs["mode"] == "SCREEN" and not attrs.get("screen"):
            raise serializers.ValidationError({"screen": "Add at least one screening condition."})
        return attrs
