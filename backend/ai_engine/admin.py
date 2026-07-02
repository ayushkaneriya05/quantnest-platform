from django.contrib import admin

from .models import AIRecommendation, MarketRegime, OverfitDetection, StrategyHealthScore


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "type", "priority", "confidence_score", "is_dismissed", "applied", "created_at"]
    list_filter = ["type", "priority", "is_dismissed", "applied"]


@admin.register(MarketRegime)
class MarketRegimeAdmin(admin.ModelAdmin):
    list_display = ["id", "instrument", "timeframe", "regime_type", "direction", "confidence", "detected_at"]
    list_filter = ["regime_type", "direction", "timeframe"]


@admin.register(StrategyHealthScore)
class StrategyHealthScoreAdmin(admin.ModelAdmin):
    list_display = ["id", "strategy", "date", "overall_score", "performance_score", "risk_score"]


@admin.register(OverfitDetection)
class OverfitDetectionAdmin(admin.ModelAdmin):
    list_display = ["id", "strategy", "backtest_run", "overfit_probability", "degradation_pct", "detected_at"]
