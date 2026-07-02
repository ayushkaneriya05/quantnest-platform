from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from strategies.models import Strategy

from .models import AIRecommendation, MarketRegime, OverfitDetection, StrategyHealthScore
from .serializers import AIRecommendationSerializer, MarketRegimeSerializer, OverfitDetectionSerializer, StrategyHealthScoreSerializer
from .services import AIEngineService


class AIRecommendationViewSet(viewsets.ModelViewSet):
    serializer_class = AIRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AIRecommendation.objects.filter(user=self.request.user).select_related("strategy")

    @action(detail=False, methods=["get"])
    def overview(self, request):
        payload = AIEngineService.overview_payload(request.user)
        return Response(
            {
                "recommendations": self.get_serializer(payload["recommendations"], many=True).data,
                "health_scores": StrategyHealthScoreSerializer(payload["health_scores"], many=True).data,
                "market_regimes": MarketRegimeSerializer(payload["market_regimes"], many=True).data,
                "overfit_detections": OverfitDetectionSerializer(payload["overfit_detections"], many=True).data,
                "latest_report": {
                    "date": payload["latest_report"].date,
                    "total_pnl": payload["latest_report"].total_pnl,
                    "total_trades": payload["latest_report"].total_trades,
                } if payload["latest_report"] else None,
            }
        )

    @action(detail=False, methods=["post"])
    def generate(self, request):
        strategy = Strategy.objects.get(id=request.data.get("strategy"), user=request.user)
        return Response(self.get_serializer(AIEngineService.generate_recommendations(strategy)).data)

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        strategy_id = request.data.get("strategy")
        if strategy_id:
            strategy = Strategy.objects.get(id=strategy_id, user=request.user)
            payload = AIEngineService.refresh_strategy_suite(strategy)
            return Response(
                {
                    "health_score": StrategyHealthScoreSerializer(payload["health_score"]).data if payload["health_score"] else None,
                    "overfit_detection": OverfitDetectionSerializer(payload["overfit_detection"]).data if payload["overfit_detection"] else None,
                    "recommendation": self.get_serializer(payload["recommendation"]).data if payload["recommendation"] else None,
                    "market_regimes": MarketRegimeSerializer(payload["market_regimes"], many=True).data,
                }
            )
        result = AIEngineService.refresh_user_suite(request.user)
        return Response({"refreshed": len(result)})

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        rec = self.get_object()
        rec.is_dismissed = True
        rec.save(update_fields=["is_dismissed", "updated_at"])
        return Response(self.get_serializer(rec).data)

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        rec = self.get_object()
        rec.applied = True
        rec.applied_at = timezone.now()
        rec.save(update_fields=["applied", "applied_at", "updated_at"])
        return Response(self.get_serializer(rec).data)


class StrategyHealthScoreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StrategyHealthScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StrategyHealthScore.objects.filter(strategy__user=self.request.user).select_related("strategy")

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        strategy = Strategy.objects.get(id=request.data.get("strategy"), user=request.user)
        return Response(self.get_serializer(AIEngineService.generate_strategy_health(strategy)).data)


class MarketRegimeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MarketRegimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MarketRegime.objects.filter(instrument__watchlistinstrument__strategy__user=self.request.user).select_related("instrument").distinct()

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        strategy = Strategy.objects.get(id=request.data.get("strategy"), user=request.user)
        regimes = []
        for watch in strategy.watchlist_instruments.select_related("instrument").all()[:5]:
            regime = AIEngineService.detect_market_regime(watch.instrument)
            if regime:
                regimes.append(regime)
        return Response(self.get_serializer(regimes, many=True).data)


class OverfitDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OverfitDetectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OverfitDetection.objects.filter(strategy__user=self.request.user).select_related("strategy", "backtest_run")

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        strategy = Strategy.objects.get(id=request.data.get("strategy"), user=request.user)
        detection = AIEngineService.detect_overfit(strategy)
        if not detection:
            return Response({})
        return Response(self.get_serializer(detection).data)
