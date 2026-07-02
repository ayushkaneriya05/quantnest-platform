from django.contrib import admin

from .models import DailySummarySchedule, Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "severity", "title", "is_read", "created_at"]
    list_filter = ["type", "severity", "is_read"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "notification_type", "in_app_enabled", "email_enabled", "push_enabled"]


@admin.register(DailySummarySchedule)
class DailySummaryScheduleAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "is_enabled", "send_time", "last_sent_at"]

