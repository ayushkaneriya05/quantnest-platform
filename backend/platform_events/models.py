from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class DomainEvent(BaseTimestampModel):
    EVENT_TYPES = [
        ("TRADE_COMPLETED", "Trade Completed"),
        ("JOURNAL_CREATED", "Journal Created"),
        ("QUIZ_COMPLETED", "Quiz Completed"),
        ("LESSON_COMPLETED", "Lesson Completed"),
        ("BACKTEST_FINISHED", "Backtest Finished"),
        ("POST_CREATED", "Post Created"),
        ("STRATEGY_DEPLOYED", "Strategy Deployed"),
        ("RISK_RULE_BROKEN", "Risk Rule Broken"),
        ("ACHIEVEMENT_UNLOCKED", "Achievement Unlocked"),
        ("PROOF_VERIFIED", "Proof Verified"),
        ("CHALLENGE_PROGRESS", "Challenge Progress"),
    ]
    STATUSES = [("PENDING", "Pending"), ("PROCESSED", "Processed"), ("FAILED", "Failed")]

    event_type = models.CharField(max_length=60, choices=EVENT_TYPES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="domain_events")
    source_app = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    idempotency_key = models.CharField(max_length=180, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "platform_domain_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.idempotency_key}"


class ActivityEvent(BaseTimestampModel):
    ACTIVITY_TYPES = [
        ("POST_CREATED", "Post Created"),
        ("FOLLOWED_USER", "Followed User"),
        ("ACHIEVEMENT_UNLOCKED", "Achievement Unlocked"),
        ("COURSE_COMPLETED", "Course Completed"),
        ("LESSON_COMPLETED", "Lesson Completed"),
        ("STRATEGY_DEPLOYED", "Strategy Deployed"),
        ("VERIFIED_TRADE", "Verified Trade"),
        ("MARKETPLACE_MILESTONE", "Marketplace Milestone"),
        ("CHALLENGE_PROGRESS", "Challenge Progress"),
        ("REPLAY_SHARED", "Replay Shared"),
    ]
    VISIBILITIES = [("PUBLIC", "Public"), ("FOLLOWERS", "Followers"), ("PRIVATE", "Private")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_events")
    activity_type = models.CharField(max_length=60, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    topic_slug = models.CharField(max_length=80, blank=True)
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_events")
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default="PUBLIC")
    metadata = models.JSONField(default=dict, blank=True)
    domain_event = models.ForeignKey(DomainEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_items")

    class Meta:
        db_table = "platform_activity_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["activity_type", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["topic_slug", "created_at"]),
            models.Index(fields=["visibility", "created_at"]),
        ]

    def __str__(self):
        return self.title

