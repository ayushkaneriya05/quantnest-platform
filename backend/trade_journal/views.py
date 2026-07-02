from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import JournalEntry, MistakeTag, TradingInsight
from .serializers import JournalEntrySerializer, MistakeTagSerializer, TradingInsightSerializer
from .services import TradeJournalService


class MistakeTagViewSet(viewsets.ModelViewSet):
    queryset = MistakeTag.objects.all()
    serializer_class = MistakeTagSerializer
    permission_classes = [permissions.IsAuthenticated]


class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user).select_related("paper_trade", "paper_trade__instrument", "live_order", "strategy")

    def perform_create(self, serializer):
        entry = serializer.save(user=self.request.user)
        try:
            from gamification.services import GamificationService
            from platform_events.services import ActivityService, DomainEventService
            from reputation.services import ReputationService

            event = DomainEventService.emit(
                "JOURNAL_CREATED",
                user=self.request.user,
                source=entry,
                source_app="trade_journal",
                payload={"title": entry.title, "rule_followed": entry.rule_followed, "setup_quality": entry.setup_quality},
            )
            ActivityService.create(
                self.request.user,
                "POST_CREATED",
                f"Logged journal insight: {entry.title}",
                summary=(entry.lessons_learned or entry.notes or "")[:240],
                target=entry,
                domain_event=event,
                visibility="PRIVATE",
                metadata={"source": "journal", "rule_followed": entry.rule_followed},
            )
            GamificationService.grant_xp(self.request.user, "JOURNAL_CREATED", 20, source=entry, metadata={"rule_followed": entry.rule_followed})
            ReputationService.recalculate_user(self.request.user)
        except Exception:
            pass

    @action(detail=False, methods=["post"])
    def bootstrap(self, request):
        created = TradeJournalService.bootstrap_recent_entries(self.request.user)
        return Response({"created": len(created)})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(TradeJournalService.journal_summary(self.request.user))


class TradingInsightViewSet(viewsets.ModelViewSet):
    serializer_class = TradingInsightSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradingInsight.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        insights = TradeJournalService.generate_insights(self.request.user)
        serializer = self.get_serializer(insights, many=True)
        return Response({"generated": len(insights), "items": serializer.data})
