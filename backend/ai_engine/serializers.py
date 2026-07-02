from rest_framework import serializers

from .models import AIRecommendation, MarketRegime, OverfitDetection, StrategyHealthScore


class AIRecommendationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = AIRecommendation
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "type",
            "title",
            "description",
            "details",
            "confidence_score",
            "priority",
            "is_dismissed",
            "applied",
            "applied_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["applied_at", "created_at", "updated_at"]


class MarketRegimeSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="instrument.sym_ticker", read_only=True)
    instrument_name = serializers.CharField(source="instrument.name", read_only=True)

    class Meta:
        model = MarketRegime
        fields = ["id", "instrument", "symbol", "instrument_name", "timeframe", "regime_type", "direction", "strength", "confidence", "detected_at", "valid_until", "created_at", "updated_at"]
        read_only_fields = ["detected_at", "created_at", "updated_at"]


class StrategyHealthScoreSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = StrategyHealthScore
        fields = ["id", "strategy", "strategy_name", "date", "overall_score", "performance_score", "risk_score", "consistency_score", "execution_score", "recommendations", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OverfitDetectionSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    backtest_run_name = serializers.CharField(source="backtest_run.name", read_only=True)

    class Meta:
        model = OverfitDetection
        fields = ["id", "strategy", "strategy_name", "backtest_run", "backtest_run_name", "overfit_probability", "in_sample_sharpe", "out_sample_sharpe", "degradation_pct", "detected_at", "created_at", "updated_at"]
        read_only_fields = ["detected_at", "created_at", "updated_at"]
