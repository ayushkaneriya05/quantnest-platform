from rest_framework import serializers

from .models import AIModerationFlag, BacktestProof, MentorProfile, MentorshipBooking, OfficeHourSession, ReputationScore, StrategyVerification, TradeReplay, TraderReputationProfile, TradingProof


class TraderReputationProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)

    class Meta:
        model = TraderReputationProfile
        fields = "__all__"
        read_only_fields = ["user", "last_calculated_at"]


class ReputationScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReputationScore
        fields = "__all__"
        read_only_fields = ["user", "calculated_at"]


class TradingProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingProof
        fields = "__all__"
        read_only_fields = ["user", "verified_at"]


class BacktestProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestProof
        fields = "__all__"
        read_only_fields = ["user", "verified_at"]


class StrategyVerificationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = StrategyVerification
        fields = "__all__"
        read_only_fields = ["user", "verified_at"]


class TradeReplaySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TradeReplay
        fields = "__all__"
        read_only_fields = ["user", "is_immutable"]


class AIModerationFlagSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AIModerationFlag
        fields = "__all__"


class MentorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = MentorProfile
        fields = "__all__"
        read_only_fields = ["user"]


class OfficeHourSessionSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source="mentor.user.username", read_only=True)

    class Meta:
        model = OfficeHourSession
        fields = "__all__"


class MentorshipBookingSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source="mentor.user.username", read_only=True)

    class Meta:
        model = MentorshipBooking
        fields = "__all__"
        read_only_fields = ["student"]

