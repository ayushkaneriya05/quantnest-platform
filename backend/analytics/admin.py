from django.contrib import admin

from .models import DailyReport, PerformanceSnapshot, StrategyComparison


@admin.register(PerformanceSnapshot)
class PerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "date", "daily_pnl", "win_rate", "sharpe_ratio_30d"]
    list_filter = ["date"]


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "date", "total_pnl", "total_trades", "winning_trades", "losing_trades"]


@admin.register(StrategyComparison)
class StrategyComparisonAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "start_date", "end_date", "created_at"]
