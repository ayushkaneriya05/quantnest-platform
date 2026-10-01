from django.utils import timezone

from common.enums import NotificationType

from .models import Notification, NotificationPreference


class NotificationService:
    @staticmethod
    def ensure_preferences(user):
        return [
            NotificationPreference.objects.get_or_create(user=user, type=notification_type)[0]
            for notification_type, _label in NotificationType.choices
        ]

    @staticmethod
    def notify(user=None, title="", message="", type=NotificationType.INFO, user_id=None, data=None, dedupe_key=None):
        if type not in NotificationType.values:
            raise ValueError(f"Unsupported notification type: {type}")
        if user is None and user_id is None:
            raise ValueError("A user or user_id is required to create a notification")
        resolved_user_id = user_id or user.pk
        preference = NotificationPreference.objects.filter(user_id=resolved_user_id, type=type).only("in_app_enabled").first()
        if preference and not preference.in_app_enabled:
            return None

        defaults = {
            "title": title,
            "message": message,
            "data": data or {},
        }
        if dedupe_key:
            notification, created = Notification.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={"user_id": resolved_user_id, "type": type, **defaults},
            )
            return notification if created else None

        return Notification.objects.create(
            user_id=resolved_user_id,
            type=type,
            **defaults,
        )

    @staticmethod
    def mark_read(notification):
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    def mark_all_read(user):
        now = timezone.now()
        return Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=now, updated_at=now
        )

    @staticmethod
    def summary(user):
        queryset = Notification.objects.filter(user=user)
        unread = queryset.filter(is_read=False)
        counts = {notification_type: unread.filter(type=notification_type).count()
                  for notification_type, _label in NotificationType.choices}
        return {
            "total": queryset.count(),
            "unread": unread.count(),
            "by_type": counts,
            "today": queryset.filter(created_at__date=timezone.localdate()).count(),
        }
