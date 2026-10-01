from collections import defaultdict

from django.db import migrations, models


TYPE_BY_OLD_EVENT = {
    "TRADE_EXECUTED": "INFO",
    "SL_HIT": "WARNING",
    "TARGET_HIT": "INFO",
    "STRATEGY_PAUSED": "WARNING",
    "STRATEGY_ERROR": "CRITICAL",
    "RISK_ALERT": "CRITICAL",
    "SYSTEM_ALERT": "INFO",
    "DAILY_SUMMARY": "INFO",
    "COMMUNITY_REPLY": "INFO",
    "COMMUNITY_MENTION": "INFO",
    "COMMUNITY_FOLLOW": "INFO",
    "BADGE_UNLOCKED": "INFO",
    "STREAK_WARNING": "WARNING",
    "CHALLENGE_PROGRESS": "INFO",
    "CERTIFICATE_ISSUED": "INFO",
    "PROOF_VERIFIED": "INFO",
    "MODERATION_ALERT": "WARNING",
}


def normalize_existing_notifications(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Preference = apps.get_model("notifications", "NotificationPreference")

    for notification in Notification.objects.only("id", "type", "severity").iterator():
        fixed_type = notification.severity
        if fixed_type not in {"INFO", "WARNING", "CRITICAL"}:
            fixed_type = TYPE_BY_OLD_EVENT.get(notification.type, "INFO")
        Notification.objects.filter(pk=notification.pk).update(type=fixed_type)

    grouped = defaultdict(list)
    for preference in Preference.objects.only("id", "user_id", "type", "in_app_enabled").iterator():
        fixed_type = TYPE_BY_OLD_EVENT.get(preference.type, "INFO")
        grouped[(preference.user_id, fixed_type)].append(preference)

    for (_user_id, fixed_type), rows in grouped.items():
        keeper = rows[0]
        enabled = all(row.in_app_enabled for row in rows)
        Preference.objects.filter(pk=keeper.pk).update(type=fixed_type, in_app_enabled=enabled)
        if len(rows) > 1:
            Preference.objects.filter(pk__in=[row.pk for row in rows[1:]]).delete()


class Migration(migrations.Migration):
    dependencies = [("notifications", "0003_alter_notification_type_and_more")]

    operations = [
        migrations.AlterUniqueTogether(
            name="notificationpreference",
            unique_together=set(),
        ),
        migrations.RenameField(
            model_name="notificationpreference",
            old_name="notification_type",
            new_name="type",
        ),
        migrations.RunPython(normalize_existing_notifications, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[("INFO", "Info"), ("WARNING", "Warning"), ("CRITICAL", "Critical")],
                default="INFO",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="dedupe_key",
            field=models.CharField(blank=True, max_length=180, null=True, unique=True),
        ),
        migrations.RemoveField(model_name="notification", name="severity"),
        migrations.AlterField(
            model_name="notificationpreference",
            name="type",
            field=models.CharField(
                choices=[("INFO", "Info"), ("WARNING", "Warning"), ("CRITICAL", "Critical")],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="notificationpreference",
            constraint=models.UniqueConstraint(
                fields=("user", "type"), name="uniq_notification_preference_user_type"
            ),
        ),
        migrations.RemoveField(model_name="notificationpreference", name="email_enabled"),
        migrations.RemoveField(model_name="notificationpreference", name="sms_enabled"),
        migrations.RemoveField(model_name="notificationpreference", name="telegram_enabled"),
        migrations.RemoveField(model_name="notificationpreference", name="telegram_chat_id"),
        migrations.RemoveField(model_name="notificationpreference", name="push_enabled"),
        migrations.RemoveField(model_name="notificationpreference", name="quiet_hours_start"),
        migrations.RemoveField(model_name="notificationpreference", name="quiet_hours_end"),
        migrations.DeleteModel(name="DailySummarySchedule"),
    ]
