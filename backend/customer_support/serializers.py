from rest_framework import serializers
from .models import Ticket, Reply


class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Reply
        fields = ["id", "body", "staff", "created_at"]
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    replies = ReplySerializer(many=True, read_only=True)
    request_type_label = serializers.CharField(source="get_request_type_display", read_only=True)
    subject = serializers.CharField(min_length=3, max_length=180, trim_whitespace=True)
    body = serializers.CharField(min_length=10, max_length=10000, trim_whitespace=True)
    def validate_request_type(self, value):
        if value == 'private':
            raise serializers.ValidationError('QuantNest Private is not available to customers. Use General enquiry for questions.')
        return value

    class Meta:
        model = Ticket
        fields = ["id", "email", "name", "request_type", "request_type_label", "subject", "body", "status", "replies", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "replies", "created_at", "updated_at"]


class ReplyInput(serializers.Serializer):
    body = serializers.CharField(min_length=2, max_length=10000, trim_whitespace=True)
