from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AchievementViewSet, AntiGamingRuleViewSet, ChallengeViewSet, GamificationMeViewSet, LeaderboardSnapshotViewSet, StreakViewSet, UserTrustFlagViewSet, XPEventViewSet, XPGrantLimitViewSet

router = DefaultRouter()
router.register(r"me", GamificationMeViewSet, basename="gamification-me")
router.register(r"xp-events", XPEventViewSet, basename="xp-event")
router.register(r"achievements", AchievementViewSet, basename="achievement")
router.register(r"streaks", StreakViewSet, basename="streak")
router.register(r"challenges", ChallengeViewSet, basename="challenge")
router.register(r"leaderboards", LeaderboardSnapshotViewSet, basename="leaderboard")
router.register(r"trust-flags", UserTrustFlagViewSet, basename="trust-flag")
router.register(r"xp-limits", XPGrantLimitViewSet, basename="xp-grant-limit")
router.register(r"anti-gaming-rules", AntiGamingRuleViewSet, basename="anti-gaming-rule")

urlpatterns = [path("", include(router.urls))]

