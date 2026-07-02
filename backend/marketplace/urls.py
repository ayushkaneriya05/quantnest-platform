from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CreatorEarningViewSet, MarketplaceListingViewSet, StrategyReviewViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"listings", MarketplaceListingViewSet, basename="marketplace-listing")
router.register(r"subscriptions", SubscriptionViewSet, basename="marketplace-subscription")
router.register(r"reviews", StrategyReviewViewSet, basename="marketplace-review")
router.register(r"earnings", CreatorEarningViewSet, basename="creator-earning")

urlpatterns = [path("", include(router.urls))]

