from django.db.models import Count
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Achievement, AntiGamingRule, Challenge, ChallengeParticipant, LeaderboardSnapshot, Streak, UserAchievement, UserTrustFlag, UserXPBalance, XPEvent, XPGrantLimit
from .serializers import (
    AchievementSerializer,
    AntiGamingRuleSerializer,
    ChallengeParticipantSerializer,
    ChallengeSerializer,
    LeaderboardSnapshotSerializer,
    StreakSerializer,
    UserAchievementSerializer,
    UserTrustFlagSerializer,
    UserXPBalanceSerializer,
    XPEventSerializer,
    XPGrantLimitSerializer,
)


class GamificationMeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        balance, _ = UserXPBalance.objects.get_or_create(user=request.user)
        return Response(
            {
                "balance": UserXPBalanceSerializer(balance).data,
                "achievements": UserAchievementSerializer(request.user.achievements.select_related("achievement")[:12], many=True).data,
                "streaks": StreakSerializer(request.user.streaks.all(), many=True).data,
                "trust_flags_open": request.user.trust_flags.filter(status__in=["OPEN", "REVIEWING"]).count(),
            }
        )


class XPEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = XPEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return XPEvent.objects.filter(user=self.request.user)


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Achievement.objects.filter(is_active=True)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        return Response(UserAchievementSerializer(request.user.achievements.select_related("achievement"), many=True).data)


class StreakViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StreakSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Streak.objects.filter(user=self.request.user)


class ChallengeViewSet(viewsets.ModelViewSet):
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Challenge.objects.filter(status__in=["ACTIVE", "COMPLETED"]).annotate(participants_count=Count("participants"))

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        challenge = self.get_object()
        participant, _ = ChallengeParticipant.objects.get_or_create(challenge=challenge, user=request.user)
        return Response(ChallengeParticipantSerializer(participant).data)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = ChallengeParticipant.objects.filter(user=request.user).select_related("challenge")
        return Response(ChallengeParticipantSerializer(qs, many=True).data)


class LeaderboardSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaderboardSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = LeaderboardSnapshot.objects.filter(eligible=True).select_related("user")
        category = self.request.query_params.get("category")
        scope = self.request.query_params.get("scope")
        if category:
            qs = qs.filter(category=category)
        if scope:
            qs = qs.filter(scope=scope)
        return qs


class UserTrustFlagViewSet(viewsets.ModelViewSet):
    serializer_class = UserTrustFlagSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = UserTrustFlag.objects.select_related("user").all()


class XPGrantLimitViewSet(viewsets.ModelViewSet):
    serializer_class = XPGrantLimitSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = XPGrantLimit.objects.all()


class AntiGamingRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AntiGamingRuleSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = AntiGamingRule.objects.all()

