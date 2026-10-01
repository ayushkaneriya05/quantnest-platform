from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    readonly_fields = ["dedupe_key", "created_at", "updated_at"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "in_app_enabled"]
    list_filter = ["type", "in_app_enabled"]
