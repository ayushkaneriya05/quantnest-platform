from rest_framework import permissions, viewsets

from community.models import Follow

from .models import ActivityEvent, DomainEvent
from .serializers import ActivityEventSerializer, DomainEventSerializer


class DomainEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DomainEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DomainEvent.objects.filter(user=self.request.user).select_related("user")


class ActivityEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ActivityEvent.objects.select_related("user", "strategy").exclude(visibility="PRIVATE")
        feed = self.request.query_params.get("feed", "for-you")
        topic = self.request.query_params.get("topic")
        strategy = self.request.query_params.get("strategy")

        if feed == "following":
            followed_ids = Follow.objects.filter(follower=self.request.user).values_list("following_id", flat=True)
            qs = qs.filter(user_id__in=followed_ids)
        elif feed == "learning":
            qs = qs.filter(activity_type__in=["COURSE_COMPLETED", "LESSON_COMPLETED", "ACHIEVEMENT_UNLOCKED"])
        elif feed == "strategy-rooms":
            qs = qs.exclude(strategy__isnull=True)

        if topic:
            qs = qs.filter(topic_slug=topic)
        if strategy:
            qs = qs.filter(strategy_id=strategy)
        return qs

