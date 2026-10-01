from django.conf import settings
from django.db import models

from common.enums import NotificationType
from common.models import BaseTimestampModel


class Notification(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.INFO)
    title = models.CharField(max_length=180)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=180, unique=True, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]


class NotificationPreference(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    type = models.CharField(max_length=20, choices=NotificationType.choices)
    in_app_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "notification_preference"
        constraints = [models.UniqueConstraint(fields=["user", "type"], name="uniq_notification_preference_user_type")]
