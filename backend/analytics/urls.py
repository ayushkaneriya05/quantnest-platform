from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DailyReportViewSet, PerformanceSnapshotViewSet, StrategyComparisonViewSet

router = DefaultRouter()
router.register(r"snapshots", PerformanceSnapshotViewSet, basename="analytics-snapshot")
router.register(r"daily-reports", DailyReportViewSet, basename="analytics-daily-report")
router.register(r"comparisons", StrategyComparisonViewSet, basename="analytics-comparison")

urlpatterns = [path("", include(router.urls))]

