from django.utils import timezone

from common.enums import NotificationType, Severity

from .models import DailySummarySchedule, Notification, NotificationPreference


class NotificationService:
    @staticmethod
    def _in_quiet_hours(preference):
        if not preference or not preference.quiet_hours_start or not preference.quiet_hours_end:
            return False
        now = timezone.localtime().time()
        start = preference.quiet_hours_start
        end = preference.quiet_hours_end
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end

    @staticmethod
    def ensure_preferences(user):
        preferences = []
        for notification_type, _label in NotificationType.choices:
            pref, _created = NotificationPreference.objects.get_or_create(
                user=user,
                notification_type=notification_type,
            )
            preferences.append(pref)
        return preferences

    @staticmethod
    def notify(user, title, message, notification_type=NotificationType.RISK_ALERT, severity=Severity.INFO, strategy=None, data=None):
        preference = NotificationPreference.objects.filter(user=user, notification_type=notification_type).first()
        if preference and not preference.in_app_enabled:
            return None
        if NotificationService._in_quiet_hours(preference):
            return None
        return Notification.objects.create(
            user=user,
            strategy=strategy,
            type=notification_type,
            severity=severity,
            title=title,
            message=message,
            data=data or {},
        )

    @staticmethod
    def mark_read(notification):
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    def get_summary_schedule(user):
        schedule, _ = DailySummarySchedule.objects.get_or_create(user=user)
        return schedule

    @staticmethod
    def mark_all_read(user):
        unread = Notification.objects.filter(user=user, is_read=False)
        now = timezone.now()
        unread.update(is_read=True, read_at=now, updated_at=now)
        return unread.count()

    @staticmethod
    def summary(user):
        queryset = Notification.objects.filter(user=user)
        return {
            "total": queryset.count(),
            "unread": queryset.filter(is_read=False).count(),
            "critical": queryset.filter(severity=Severity.CRITICAL, is_read=False).count(),
            "today": queryset.filter(created_at__date=timezone.localdate()).count(),
        }
