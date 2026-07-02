from django.conf import settings
from django.db import models
from datetime import time

from common.enums import NotificationType, Severity
from common.models import BaseTimestampModel


class Notification(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    title = models.CharField(max_length=180)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]


class NotificationPreference(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    sms_enabled = models.BooleanField(default=False)
    telegram_enabled = models.BooleanField(default=False)
    telegram_chat_id = models.CharField(max_length=80, blank=True)
    push_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = "notification_preference"
        unique_together = ["user", "notification_type"]


class DailySummarySchedule(BaseTimestampModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_summary_schedule")
    is_enabled = models.BooleanField(default=True)
    send_time = models.TimeField(default=time(18, 0))
    include_pnl = models.BooleanField(default=True)
    include_trades = models.BooleanField(default=True)
    include_insights = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "daily_summary_schedule"
