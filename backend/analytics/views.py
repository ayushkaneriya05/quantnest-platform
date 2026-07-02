from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from strategies.models import Strategy

from .models import DailyReport, PerformanceSnapshot, StrategyComparison
from .serializers import DailyReportSerializer, PerformanceSnapshotSerializer, StrategyComparisonSerializer
from .services import AnalyticsService


class PerformanceSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PerformanceSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PerformanceSnapshot.objects.filter(user=self.request.user).select_related("strategy")

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        strategy_id = request.data.get("strategy")
        if strategy_id:
            strategy = Strategy.objects.get(id=strategy_id, user=request.user)
            snapshot = AnalyticsService.refresh_strategy_snapshot(request.user, strategy)
            return Response(self.get_serializer(snapshot).data)
        report = AnalyticsService.refresh_phase7_suite(request.user)
        return Response(DailyReportSerializer(report).data)


class DailyReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DailyReport.objects.filter(user=self.request.user).select_related("best_strategy", "worst_strategy")

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        payload = AnalyticsService.dashboard_payload(request.user)
        return Response(
            {
                "latest_report": DailyReportSerializer(payload["latest_report"]).data if payload["latest_report"] else None,
                "snapshots": PerformanceSnapshotSerializer(payload["snapshots"], many=True).data,
                "comparisons": StrategyComparisonSerializer(payload["comparisons"], many=True).data,
                "insights": [
                    {
                        "id": item.id,
                        "insight_type": item.insight_type,
                        "title": item.title,
                        "description": item.description,
                        "related_trades": item.related_trades,
                        "generated_at": item.generated_at,
                    }
                    for item in payload["insights"]
                ],
                "notification_summary": payload["notification_summary"],
                "journal_summary": payload["journal_summary"],
            }
        )


class StrategyComparisonViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StrategyComparison.objects.filter(user=self.request.user).prefetch_related("strategies")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        strategies = serializer.validated_data.get("strategies") or []
        comparison = AnalyticsService.compare_strategies(
            self.request.user,
            [strategy for strategy in strategies if strategy.user_id == self.request.user.id],
            serializer.validated_data["start_date"],
            serializer.validated_data["end_date"],
        )
        return Response(self.get_serializer(comparison).data)
