from rest_framework import serializers

from .models import (
    Achievement,
    AntiGamingRule,
    Challenge,
    ChallengeParticipant,
    LeaderboardSnapshot,
    Streak,
    UserAchievement,
    UserTrustFlag,
    UserXPBalance,
    XPEvent,
    XPGrantLimit,
)


class XPEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = XPEvent
        fields = ["id", "username", "source_type", "source_model", "source_id", "points", "quality_score", "metadata", "created_at"]
        read_only_fields = fields


class UserXPBalanceSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserXPBalance
        fields = ["id", "username", "total_xp", "level", "weekly_xp", "monthly_xp", "created_at", "updated_at"]
        read_only_fields = fields


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = "__all__"


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source="achievement.name", read_only=True)
    achievement_category = serializers.CharField(source="achievement.category", read_only=True)

    class Meta:
        model = UserAchievement
        fields = ["id", "achievement", "achievement_name", "achievement_category", "unlocked_at", "metadata"]
        read_only_fields = ["unlocked_at"]


class StreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = Streak
        fields = "__all__"
        read_only_fields = ["user"]


class ChallengeSerializer(serializers.ModelSerializer):
    participants_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Challenge
        fields = "__all__"


class ChallengeParticipantSerializer(serializers.ModelSerializer):
    challenge_title = serializers.CharField(source="challenge.title", read_only=True)

    class Meta:
        model = ChallengeParticipant
        fields = ["id", "challenge", "challenge_title", "status", "progress", "score", "completed_at", "created_at", "updated_at"]
        read_only_fields = ["completed_at", "created_at", "updated_at"]


class LeaderboardSnapshotSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)

    class Meta:
        model = LeaderboardSnapshot
        fields = ["id", "username", "avatar", "category", "scope", "rank", "score", "metrics", "eligible", "snapshot_date", "created_at"]
        read_only_fields = fields


class UserTrustFlagSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserTrustFlag
        fields = "__all__"


class XPGrantLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = XPGrantLimit
        fields = "__all__"


class AntiGamingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntiGamingRule
        fields = "__all__"

