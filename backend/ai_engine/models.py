from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class AIRecommendation(BaseTimestampModel):
    TYPES = [
        ("RULE_SUGGESTION", "Rule Suggestion"),
        ("PARAMETER_TUNING", "Parameter Tuning"),
        ("OVERFIT_WARNING", "Overfit Warning"),
        ("REGIME_CHANGE", "Regime Change"),
        ("RISK_ALERT", "Risk Alert"),
    ]
    PRIORITIES = [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_recommendations")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="ai_recommendations")
    type = models.CharField(max_length=40, choices=TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default="MEDIUM")
    is_dismissed = models.BooleanField(default=False)
    applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_recommendation"
        ordering = ["-created_at"]


class MarketRegime(BaseTimestampModel):
    REGIMES = [
        ("TRENDING", "Trending"),
        ("RANGING", "Ranging"),
        ("HIGH_VOLATILITY", "High Volatility"),
        ("LOW_VOLATILITY", "Low Volatility"),
        ("BREAKOUT", "Breakout"),
    ]
    DIRECTIONS = [("BULLISH", "Bullish"), ("BEARISH", "Bearish"), ("NEUTRAL", "Neutral")]

    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="market_regimes")
    timeframe = models.CharField(max_length=10, default="1D")
    regime_type = models.CharField(max_length=20, choices=REGIMES)
    direction = models.CharField(max_length=20, choices=DIRECTIONS, default="NEUTRAL")
    strength = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    confidence = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    detected_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "market_regime"
        ordering = ["-detected_at"]


class StrategyHealthScore(BaseTimestampModel):
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="health_scores")
    date = models.DateField()
    overall_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    performance_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    consistency_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    execution_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    recommendations = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "strategy_health_score"
        unique_together = ["strategy", "date"]
        ordering = ["-date"]


class OverfitDetection(BaseTimestampModel):
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="overfit_detections")
    backtest_run = models.ForeignKey("backtesting.BacktestRun", on_delete=models.CASCADE, related_name="overfit_detections")
    overfit_probability = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    in_sample_sharpe = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    out_sample_sharpe = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    degradation_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "overfit_detection"
        ordering = ["-detected_at"]

