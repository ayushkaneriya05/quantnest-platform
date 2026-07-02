from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BacktestProofViewSet, StrategyVerificationViewSet, TradingProofViewSet

router = DefaultRouter()
router.register(r"trading", TradingProofViewSet, basename="proof-trading")
router.register(r"backtests", BacktestProofViewSet, basename="proof-backtest")
router.register(r"strategies", StrategyVerificationViewSet, basename="proof-strategy")

urlpatterns = [path("", include(router.urls))]

