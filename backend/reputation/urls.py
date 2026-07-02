from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIModerationFlagViewSet, BacktestProofViewSet, MentorProfileViewSet, MentorshipBookingViewSet, OfficeHourSessionViewSet, ReputationScoreViewSet, StrategyVerificationViewSet, TradeReplayViewSet, TraderReputationProfileViewSet, TradingProofViewSet

router = DefaultRouter()
router.register(r"profiles", TraderReputationProfileViewSet, basename="trader-reputation")
router.register(r"scores", ReputationScoreViewSet, basename="reputation-score")
router.register(r"trading-proofs", TradingProofViewSet, basename="trading-proof")
router.register(r"backtest-proofs", BacktestProofViewSet, basename="backtest-proof")
router.register(r"strategy-verifications", StrategyVerificationViewSet, basename="strategy-verification")
router.register(r"replays", TradeReplayViewSet, basename="trade-replay")
router.register(r"moderation-flags", AIModerationFlagViewSet, basename="ai-moderation-flag")
router.register(r"mentors", MentorProfileViewSet, basename="mentor-profile")
router.register(r"office-hours", OfficeHourSessionViewSet, basename="office-hour")
router.register(r"bookings", MentorshipBookingViewSet, basename="mentorship-booking")

urlpatterns = [path("", include(router.urls))]

