from django.db.models import Count

from platform_events.services import ActivityService, DomainEventService


class CommunityService:
    @staticmethod
    def publish_post(post):
        event = DomainEventService.emit(
            "POST_CREATED",
            user=post.author,
            source=post,
            source_app="community",
            payload={"post_type": post.post_type, "title": post.title, "topic": post.topic.slug if post.topic else ""},
        )
        ActivityService.create(
            post.author,
            "POST_CREATED",
            post.title,
            summary=post.body[:240],
            target=post,
            domain_event=event,
            topic_slug=post.topic.slug if post.topic else "",
            strategy=post.strategy_room.strategy if post.strategy_room else None,
            visibility=post.visibility,
            metadata={"post_type": post.post_type, "verified": post.is_verified_claim},
        )
        try:
            from gamification.services import GamificationService

            GamificationService.grant_xp(post.author, "POST_CREATED", 5, source=post, metadata={"post_type": post.post_type})
        except Exception:
            pass
        return event

    @staticmethod
    def topic_summary():
        from .models import Topic

        return Topic.objects.annotate(active_posts=Count("posts")).order_by("-is_featured", "name")

