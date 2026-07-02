from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DailySummaryScheduleViewSet, NotificationPreferenceViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r"items", NotificationViewSet, basename="notification")
router.register(r"preferences", NotificationPreferenceViewSet, basename="notification-preference")
router.register(r"summary-schedule", DailySummaryScheduleViewSet, basename="summary-schedule")

urlpatterns = [path("", include(router.urls))]

