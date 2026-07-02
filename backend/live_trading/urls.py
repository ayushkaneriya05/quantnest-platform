from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ExecutionLogViewSet,
    LiveOrderViewSet,
    LivePositionViewSet,
    LiveStrategyAllocationViewSet,
    SlippageRecordViewSet,
    TradingSessionViewSet,
)

router = DefaultRouter()
router.register(r"sessions", TradingSessionViewSet, basename="live-session")
router.register(r"orders", LiveOrderViewSet, basename="live-order")
router.register(r"positions", LivePositionViewSet, basename="live-position")
router.register(r"allocations", LiveStrategyAllocationViewSet, basename="live-allocation")
router.register(r"execution-logs", ExecutionLogViewSet, basename="live-execution-log")
router.register(r"slippage", SlippageRecordViewSet, basename="live-slippage")

urlpatterns = [path("", include(router.urls))]
