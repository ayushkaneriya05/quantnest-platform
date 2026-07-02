from rest_framework import serializers

from .models import (
    Bookmark,
    Comment,
    CommunityProfile,
    Follow,
    ModerationAction,
    Post,
    PostAttachment,
    PostReport,
    Reaction,
    StrategyRoom,
    Topic,
)


class CommunityProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)
    bio = serializers.CharField(source="user.bio", read_only=True)

    class Meta:
        model = CommunityProfile
        fields = [
            "id",
            "username",
            "avatar",
            "bio",
            "display_name",
            "headline",
            "trader_level",
            "preferred_markets",
            "social_links",
            "is_discoverable",
            "show_reputation",
            "show_learning_progress",
            "show_verified_metrics",
            "selected_badges",
            "trader_archetype",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "name", "slug", "description", "is_featured", "posts_count", "created_at", "updated_at"]
        read_only_fields = ["posts_count", "created_at", "updated_at"]


class StrategyRoomSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = StrategyRoom
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "listing",
            "owner",
            "owner_name",
            "title",
            "description",
            "room_type",
            "is_active",
            "pinned_post",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["owner", "owner_name", "created_at", "updated_at"]


class PostAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAttachment
        fields = ["id", "attachment_type", "url", "metadata", "created_at"]
        read_only_fields = ["created_at"]


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)
    author_avatar = serializers.URLField(source="author.avatar", read_only=True)
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)
    strategy_room_title = serializers.CharField(source="strategy_room.title", read_only=True)
    attachments = PostAttachmentSerializer(many=True, read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "author_name",
            "author_avatar",
            "topic",
            "topic_name",
            "topic_slug",
            "strategy_room",
            "strategy_room_title",
            "post_type",
            "title",
            "body",
            "visibility",
            "status",
            "hashtags",
            "mentions",
            "poll_options",
            "poll_expires_at",
            "source_type",
            "source_id",
            "sanitized_snapshot",
            "chart_embed",
            "is_pinned",
            "is_verified_claim",
            "helpful_score",
            "attachments",
            "reactions_count",
            "comments_count",
            "is_bookmarked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "helpful_score", "created_at", "updated_at"]

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.bookmarks.filter(user=request.user).exists()


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "author_name", "parent", "body", "mentions", "is_hidden", "helpful_score", "created_at", "updated_at"]
        read_only_fields = ["author", "is_hidden", "helpful_score", "created_at", "updated_at"]


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = ["id", "post", "comment", "reaction_type", "created_at"]
        read_only_fields = ["created_at"]


class BookmarkSerializer(serializers.ModelSerializer):
    post_detail = PostSerializer(source="post", read_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "post", "post_detail", "created_at"]
        read_only_fields = ["created_at"]


class FollowSerializer(serializers.ModelSerializer):
    follower_name = serializers.CharField(source="follower.username", read_only=True)
    following_name = serializers.CharField(source="following.username", read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "follower_name", "following", "following_name", "created_at"]
        read_only_fields = ["follower", "created_at"]


class PostReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True)

    class Meta:
        model = PostReport
        fields = ["id", "reporter", "reporter_name", "post", "comment", "reason", "details", "status", "created_at", "updated_at"]
        read_only_fields = ["reporter", "status", "created_at", "updated_at"]


class ModerationActionSerializer(serializers.ModelSerializer):
    moderator_name = serializers.CharField(source="moderator.username", read_only=True)

    class Meta:
        model = ModerationAction
        fields = ["id", "moderator", "moderator_name", "post", "comment", "action", "reason", "metadata", "created_at", "updated_at"]
        read_only_fields = ["moderator", "created_at", "updated_at"]

