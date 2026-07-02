from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookmarkViewSet,
    CommentViewSet,
    CommunityProfileViewSet,
    FollowViewSet,
    ModerationActionViewSet,
    PostReportViewSet,
    PostViewSet,
    StrategyRoomViewSet,
    TopicViewSet,
    StrategyRoomByStrategyView,
)

router = DefaultRouter()
router.register(r"profiles", CommunityProfileViewSet, basename="community-profile")
router.register(r"topics", TopicViewSet, basename="community-topic")
router.register(r"posts", PostViewSet, basename="community-post")
router.register(r"comments", CommentViewSet, basename="community-comment")
router.register(r"bookmarks", BookmarkViewSet, basename="community-bookmark")
router.register(r"follows", FollowViewSet, basename="community-follow")
router.register(r"reports", PostReportViewSet, basename="community-report")
router.register(r"moderation", ModerationActionViewSet, basename="community-moderation")
router.register(r"strategy-rooms", StrategyRoomViewSet, basename="community-strategy-room")

urlpatterns = [
    path("strategies/<int:strategy_id>/rooms/", StrategyRoomByStrategyView.as_view(), name="strategy-room-by-strategy"),
    path("", include(router.urls)),
]
