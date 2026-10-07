from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor_name", "action", "entity_type", "entity_type_display", "entity_id", "entity_name", "reason",
                  "old_value", "new_value", "ip_address", "timestamp"]
        read_only_fields = fields
