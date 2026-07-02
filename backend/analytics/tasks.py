from celery import shared_task
from django.contrib.auth import get_user_model

from .services import AnalyticsService


@shared_task(name="analytics.refresh_daily_reports")
def refresh_daily_reports():
    refreshed = 0
    for user in get_user_model().objects.all():
        AnalyticsService.refresh_user_daily_report(user)
        refreshed += 1
    return {"users_refreshed": refreshed}

