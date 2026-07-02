from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from analytics.models import DailyReport
from common.enums import NotificationType, Severity

from .models import DailySummarySchedule
from .services import NotificationService


@shared_task(name="notifications.dispatch_daily_summaries")
def dispatch_daily_summaries():
    sent = 0
    target_time = timezone.localtime().time().replace(second=0, microsecond=0)
    for schedule in DailySummarySchedule.objects.filter(is_enabled=True).select_related("user"):
        if schedule.last_sent_at and schedule.last_sent_at.date() == timezone.localdate():
            continue
        if schedule.send_time and schedule.send_time.hour != target_time.hour:
            continue
        report = DailyReport.objects.filter(user=schedule.user, date=timezone.localdate()).first()
        if not report:
            continue
        parts = []
        if schedule.include_pnl:
            parts.append(f"PnL: {report.total_pnl}")
        if schedule.include_trades:
            parts.append(f"Trades: {report.total_trades}")
        NotificationService.notify(
            schedule.user,
            title="Daily Trading Summary",
            message=" | ".join(parts) or "Daily summary available",
            notification_type=NotificationType.DAILY_SUMMARY,
            severity=Severity.INFO,
            data={"report_id": report.id},
        )
        schedule.last_sent_at = timezone.now()
        schedule.save(update_fields=["last_sent_at", "updated_at"])
        sent += 1
    return {"sent": sent}

