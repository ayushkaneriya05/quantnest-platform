from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AIModerationFlag, BacktestProof, MentorProfile, MentorshipBooking, OfficeHourSession, ReputationScore, StrategyVerification, TradeReplay, TraderReputationProfile, TradingProof
from .serializers import AIModerationFlagSerializer, BacktestProofSerializer, MentorProfileSerializer, MentorshipBookingSerializer, OfficeHourSessionSerializer, ReputationScoreSerializer, StrategyVerificationSerializer, TradeReplaySerializer, TraderReputationProfileSerializer, TradingProofSerializer
from .services import ReputationService


class TraderReputationProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TraderReputationProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TraderReputationProfile.objects.select_related("user")

    @action(detail=False, methods=["get", "post"])
    def me(self, request):
        profile = ReputationService.recalculate_user(request.user) if request.method == "POST" else TraderReputationProfile.objects.get_or_create(user=request.user)[0]
        return Response(self.get_serializer(profile).data)


class ReputationScoreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReputationScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReputationScore.objects.filter(user=self.request.user)


class TradingProofViewSet(viewsets.ModelViewSet):
    serializer_class = TradingProofSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradingProof.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BacktestProofViewSet(viewsets.ModelViewSet):
    serializer_class = BacktestProofSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BacktestProof.objects.filter(user=self.request.user).select_related("backtest_run")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StrategyVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StrategyVerification.objects.filter(user=self.request.user).select_related("strategy")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TradeReplayViewSet(viewsets.ModelViewSet):
    serializer_class = TradeReplaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradeReplay.objects.filter(user=self.request.user) | TradeReplay.objects.filter(visibility="PUBLIC")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        replay = self.get_object()
        replay.visibility = request.data.get("visibility", "PUBLIC")
        replay.is_immutable = True
        replay.save(update_fields=["visibility", "is_immutable", "updated_at"])
        return Response(self.get_serializer(replay).data)


class AIModerationFlagViewSet(viewsets.ModelViewSet):
    serializer_class = AIModerationFlagSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = AIModerationFlag.objects.select_related("user").all()


class MentorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = MentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MentorProfile.objects.filter(is_accepting_sessions=True) | MentorProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        profile, _ = MentorProfile.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(profile).data)


class OfficeHourSessionViewSet(viewsets.ModelViewSet):
    serializer_class = OfficeHourSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = OfficeHourSession.objects.select_related("mentor", "mentor__user").all()


class MentorshipBookingViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MentorshipBooking.objects.filter(student=self.request.user).select_related("mentor", "mentor__user", "session")

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

