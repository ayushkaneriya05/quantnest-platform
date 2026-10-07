from django.conf import settings
from django.db import models
from common.models import BaseTimestampModel
from common.enums import ActivityResource

class AuditLog(BaseTimestampModel):
    ACTIONS = [(value, value.replace("_", " ").title()) for value in
               ("CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "DEPLOY", "PAUSE", "RESUME",
                "STOP_REQUESTED", "STOP", "ALLOCATE", "DEALLOCATE", "RESET")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    actor_name = models.CharField(max_length=150, default="System")
    action = models.CharField(max_length=20, choices=ACTIONS)
    entity_type = models.CharField(max_length=80, choices=ActivityResource.choices)
    entity_id = models.CharField(max_length=80, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp", "-id"]
        indexes = [models.Index(fields=["user", "-timestamp"], name="audit_user_time_idx")]
        constraints = [models.CheckConstraint(condition=models.Q(entity_type__in=ActivityResource.values), name="audit_supported_resource")]

