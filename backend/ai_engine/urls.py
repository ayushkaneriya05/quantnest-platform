from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIRecommendationViewSet, MarketRegimeViewSet, OverfitDetectionViewSet, StrategyHealthScoreViewSet

router = DefaultRouter()
router.register(r"recommendations", AIRecommendationViewSet, basename="ai-recommendation")
router.register(r"health-scores", StrategyHealthScoreViewSet, basename="strategy-health-score")
router.register(r"market-regimes", MarketRegimeViewSet, basename="market-regime")
router.register(r"overfit", OverfitDetectionViewSet, basename="overfit-detection")

urlpatterns = [path("", include(router.urls))]

