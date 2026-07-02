from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class PerformanceSnapshot(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="performance_snapshots")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="performance_snapshots")
    date = models.DateField()
    daily_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cumulative_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    trades_count = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    win_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avg_trade_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    sharpe_ratio_30d = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    class Meta:
        db_table = "analytics_performance_snapshot"
        unique_together = ["user", "strategy", "date"]
        ordering = ["-date"]


class DailyReport(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_reports")
    date = models.DateField()
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_trades = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    best_trade = models.JSONField(default=dict, blank=True)
    worst_trade = models.JSONField(default=dict, blank=True)
    best_strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="best_daily_reports")
    worst_strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="worst_daily_reports")

    class Meta:
        db_table = "analytics_daily_report"
        unique_together = ["user", "date"]
        ordering = ["-date"]


class StrategyComparison(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_comparisons")
    strategies = models.ManyToManyField("strategies.Strategy", related_name="comparisons")
    start_date = models.DateField()
    end_date = models.DateField()
    comparison_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_strategy_comparison"
        ordering = ["-created_at"]

