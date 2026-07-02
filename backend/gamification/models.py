from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class XPGrantLimit(BaseTimestampModel):
    source_type = models.CharField(max_length=80, unique=True)
    daily_limit = models.PositiveIntegerField(default=100)
    cooldown_seconds = models.PositiveIntegerField(default=0)
    min_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gamification_xp_grant_limit"


class XPEvent(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_events")
    source_type = models.CharField(max_length=80)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    points = models.IntegerField()
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=180, unique=True)

    class Meta:
        db_table = "gamification_xp_event"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "source_type", "created_at"])]


class UserXPBalance(BaseTimestampModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_balance")
    total_xp = models.IntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    weekly_xp = models.IntegerField(default=0)
    monthly_xp = models.IntegerField(default=0)

    class Meta:
        db_table = "gamification_user_xp_balance"


class Achievement(BaseTimestampModel):
    CATEGORIES = [
        ("COMMUNITY", "Community"),
        ("LEARNING", "Learning"),
        ("DISCIPLINE", "Discipline"),
        ("TRADING", "Trading"),
        ("CREATOR", "Creator"),
        ("VERIFICATION", "Verification"),
    ]

    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORIES)
    xp_reward = models.PositiveIntegerField(default=0)
    badge_icon = models.CharField(max_length=80, blank=True)
    criteria = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gamification_achievement"
        ordering = ["category", "name"]


class UserAchievement(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="user_awards")
    unlocked_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_user_achievement"
        unique_together = ["user", "achievement"]
        ordering = ["-unlocked_at"]


class Streak(BaseTimestampModel):
    STREAK_TYPES = [
        ("JOURNAL", "Journal"),
        ("LEARNING", "Learning"),
        ("RULE_DISCIPLINE", "Rule Discipline"),
        ("PAPER_TRADING", "Paper Trading"),
        ("COMMUNITY_HELPFULNESS", "Community Helpfulness"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streaks")
    streak_type = models.CharField(max_length=40, choices=STREAK_TYPES)
    current_count = models.PositiveIntegerField(default=0)
    longest_count = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    freeze_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gamification_streak"
        unique_together = ["user", "streak_type"]


class Challenge(BaseTimestampModel):
    CHALLENGE_TYPES = [
        ("MARKET_REPLAY", "Market Replay"),
        ("CRASH_SURVIVAL", "Crash Survival"),
        ("LOW_CAPITAL", "Low Capital"),
        ("PROP_FIRM", "Prop Firm"),
        ("NEWS_EVENT", "News Event"),
        ("DRAWDOWN_DISCIPLINE", "Drawdown Discipline"),
        ("RISK_ONLY", "Risk Only"),
    ]
    STATUSES = [("DRAFT", "Draft"), ("ACTIVE", "Active"), ("COMPLETED", "Completed"), ("ARCHIVED", "Archived")]

    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    challenge_type = models.CharField(max_length=40, choices=CHALLENGE_TYPES)
    rules = models.JSONField(default=dict, blank=True)
    reward_xp = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = "gamification_challenge"
        ordering = ["-is_featured", "-created_at"]


class ChallengeParticipant(BaseTimestampModel):
    STATUSES = [("JOINED", "Joined"), ("IN_PROGRESS", "In Progress"), ("PASSED", "Passed"), ("FAILED", "Failed"), ("ABANDONED", "Abandoned")]

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_participations")
    status = models.CharField(max_length=20, choices=STATUSES, default="JOINED")
    progress = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gamification_challenge_participant"
        unique_together = ["challenge", "user"]
        ordering = ["-updated_at"]


class LeaderboardSnapshot(BaseTimestampModel):
    CATEGORIES = [
        ("OVERALL", "Overall"),
        ("COMMUNITY_HELPFULNESS", "Community Helpfulness"),
        ("LEARNING_XP", "Learning XP"),
        ("JOURNAL_DISCIPLINE", "Journal Discipline"),
        ("PAPER_PERFORMANCE", "Paper Performance"),
        ("RISK_DISCIPLINE", "Risk Discipline"),
        ("CREATOR_REPUTATION", "Creator Reputation"),
        ("VERIFIED_TRADER_SCORE", "Verified Trader Score"),
    ]
    SCOPES = [("WEEKLY", "Weekly"), ("MONTHLY", "Monthly"), ("ALL_TIME", "All Time")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leaderboard_snapshots")
    category = models.CharField(max_length=40, choices=CATEGORIES)
    scope = models.CharField(max_length=20, choices=SCOPES, default="WEEKLY")
    rank = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=12, decimal_places=2)
    metrics = models.JSONField(default=dict, blank=True)
    eligible = models.BooleanField(default=True)
    snapshot_date = models.DateField()

    class Meta:
        db_table = "gamification_leaderboard_snapshot"
        unique_together = ["user", "category", "scope", "snapshot_date"]
        ordering = ["category", "scope", "rank"]


class UserTrustFlag(BaseTimestampModel):
    FLAG_TYPES = [("XP_FARMING", "XP Farming"), ("BOT_BEHAVIOR", "Bot Behavior"), ("FAKE_CLAIM", "Fake Claim"), ("LOW_QUALITY", "Low Quality"), ("MANUAL_REVIEW", "Manual Review")]
    STATUSES = [("OPEN", "Open"), ("REVIEWING", "Reviewing"), ("RESOLVED", "Resolved"), ("DISMISSED", "Dismissed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_flags")
    flag_type = models.CharField(max_length=40, choices=FLAG_TYPES)
    severity = models.CharField(max_length=20, default="WARNING")
    reason = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="OPEN")

    class Meta:
        db_table = "gamification_user_trust_flag"
        ordering = ["-created_at"]


class AntiGamingRule(BaseTimestampModel):
    code = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    rule_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gamification_anti_gaming_rule"

