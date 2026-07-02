from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class CommunityProfile(BaseTimestampModel):
    TRADER_LEVELS = [("BEGINNER", "Beginner"), ("INTERMEDIATE", "Intermediate"), ("ADVANCED", "Advanced"), ("PRO", "Professional")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_profile")
    display_name = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=180, blank=True)
    trader_level = models.CharField(max_length=20, choices=TRADER_LEVELS, default="BEGINNER")
    preferred_markets = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    is_discoverable = models.BooleanField(default=True)
    show_reputation = models.BooleanField(default=True)
    show_learning_progress = models.BooleanField(default=True)
    show_verified_metrics = models.BooleanField(default=False)
    selected_badges = models.JSONField(default=list, blank=True)
    trader_archetype = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "community_profile"
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name or self.user.username or self.user.email


class Topic(BaseTimestampModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    posts_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "community_topic"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StrategyRoom(BaseTimestampModel):
    ROOM_TYPES = [("PUBLIC", "Public"), ("SUBSCRIBERS", "Subscribers"), ("CREATOR_ONLY", "Creator Only")]

    strategy = models.OneToOneField("strategies.Strategy", on_delete=models.CASCADE, related_name="community_room")
    listing = models.OneToOneField("marketplace.MarketplaceListing", on_delete=models.SET_NULL, null=True, blank=True, related_name="community_room")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_strategy_rooms")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="PUBLIC")
    is_active = models.BooleanField(default=True)
    pinned_post = models.ForeignKey("community.Post", on_delete=models.SET_NULL, null=True, blank=True, related_name="pinned_in_rooms")

    class Meta:
        db_table = "community_strategy_room"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Post(BaseTimestampModel):
    POST_TYPES = [
        ("TEXT", "Text"),
        ("QUESTION", "Question"),
        ("TRADE_REVIEW", "Trade Review"),
        ("JOURNAL_LESSON", "Journal Lesson"),
        ("STRATEGY_NOTE", "Strategy Note"),
        ("POLL", "Poll"),
        ("MILESTONE", "Milestone"),
        ("COURSE_COMPLETION", "Course Completion"),
        ("MARKET_EVENT_REACTION", "Market Event Reaction"),
    ]
    VISIBILITIES = [("PUBLIC", "Public"), ("FOLLOWERS", "Followers"), ("PRIVATE", "Private")]
    STATUSES = [("PUBLISHED", "Published"), ("DRAFT", "Draft"), ("HIDDEN", "Hidden"), ("LOCKED", "Locked")]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_posts")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    strategy_room = models.ForeignKey(StrategyRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    post_type = models.CharField(max_length=40, choices=POST_TYPES, default="TEXT")
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default="PUBLIC")
    status = models.CharField(max_length=20, choices=STATUSES, default="PUBLISHED")
    hashtags = models.JSONField(default=list, blank=True)
    mentions = models.JSONField(default=list, blank=True)
    poll_options = models.JSONField(default=list, blank=True)
    poll_expires_at = models.DateTimeField(null=True, blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    sanitized_snapshot = models.JSONField(default=dict, blank=True)
    chart_embed = models.JSONField(default=dict, blank=True)
    is_pinned = models.BooleanField(default=False)
    is_verified_claim = models.BooleanField(default=False)
    helpful_score = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "community_post"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post_type", "created_at"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["status", "visibility", "created_at"]),
        ]

    def __str__(self):
        return self.title


class PostAttachment(BaseTimestampModel):
    ATTACHMENT_TYPES = [("IMAGE", "Image"), ("CHART", "Chart"), ("REPLAY", "Replay"), ("FILE", "File")]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="attachments")
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)
    url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "community_post_attachment"


class Comment(BaseTimestampModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    body = models.TextField()
    mentions = models.JSONField(default=list, blank=True)
    is_hidden = models.BooleanField(default=False)
    helpful_score = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "community_comment"
        ordering = ["created_at"]


class Reaction(BaseTimestampModel):
    REACTIONS = [("LIKE", "Like"), ("INSIGHTFUL", "Insightful"), ("HELPFUL", "Helpful"), ("VERIFY", "Verify"), ("CAUTION", "Caution")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_reactions")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="reactions")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="reactions")
    reaction_type = models.CharField(max_length=20, choices=REACTIONS, default="LIKE")

    class Meta:
        db_table = "community_reaction"
        unique_together = [("user", "post", "reaction_type"), ("user", "comment", "reaction_type")]


class Bookmark(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")

    class Meta:
        db_table = "community_bookmark"
        unique_together = ["user", "post"]


class Follow(BaseTimestampModel):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_edges")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_edges")

    class Meta:
        db_table = "community_follow"
        unique_together = ["follower", "following"]


class PostReport(BaseTimestampModel):
    REPORT_REASONS = [
        ("SPAM", "Spam"),
        ("ABUSE", "Abuse"),
        ("FAKE_PNL", "Fake PnL"),
        ("PUMP_DUMP", "Pump and Dump"),
        ("MISLEADING", "Misleading"),
        ("OTHER", "Other"),
    ]
    STATUSES = [("OPEN", "Open"), ("REVIEWING", "Reviewing"), ("RESOLVED", "Resolved"), ("DISMISSED", "Dismissed")]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_reports")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=30, choices=REPORT_REASONS)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="OPEN")

    class Meta:
        db_table = "community_post_report"
        ordering = ["-created_at"]


class ModerationAction(BaseTimestampModel):
    ACTIONS = [("HIDE", "Hide"), ("LOCK", "Lock"), ("WARN", "Warn"), ("SUSPEND", "Suspend"), ("DISMISS_REPORT", "Dismiss Report")]

    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_actions")
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_actions")
    comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_actions")
    action = models.CharField(max_length=30, choices=ACTIONS)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "community_moderation_action"
        ordering = ["-created_at"]

