from django.contrib import admin

from .models import ActivityEvent, DomainEvent


@admin.register(DomainEvent)
class DomainEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "source_app", "status", "created_at")
    search_fields = ("event_type", "idempotency_key", "source_model", "source_id")
    list_filter = ("event_type", "status", "source_app")


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("activity_type", "user", "title", "visibility", "created_at")
    search_fields = ("title", "summary", "target_type", "target_id")
    list_filter = ("activity_type", "visibility")
