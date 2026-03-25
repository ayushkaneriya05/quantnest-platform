from django.contrib import admin
from .models import (
    BacktestRun, BacktestTrade, BacktestMetrics, EquityCurvePoint,
    OptimizationRun, OptimizationResult, MonteCarloRun, MonteCarloResult
)


@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy', 'user', 'status', 'start_date', 'end_date', 'progress_pct', 'created_at']
    list_filter = ['status', 'data_resolution']
    search_fields = ['name', 'strategy__name', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']


@admin.register(BacktestTrade)
class BacktestTradeAdmin(admin.ModelAdmin):
    list_display = ['run', 'instrument', 'side', 'entry_time', 'exit_time', 'net_pnl', 'pnl_pct']
    list_filter = ['side', 'exit_reason']
    search_fields = ['run__name', 'instrument__symbol']


@admin.register(BacktestMetrics)
class BacktestMetricsAdmin(admin.ModelAdmin):
    list_display = ['run', 'total_trades', 'win_rate', 'profit_factor', 'sharpe_ratio', 'max_drawdown_pct', 'total_return_pct']


@admin.register(EquityCurvePoint)
class EquityCurvePointAdmin(admin.ModelAdmin):
    list_display = ['run', 'timestamp', 'equity_value', 'drawdown_pct']
    list_filter = ['run']


@admin.register(OptimizationRun)
class OptimizationRunAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy', 'user', 'optimization_metric', 'status', 'total_combinations', 'completed_combinations']
    list_filter = ['status', 'optimization_metric']
    search_fields = ['name', 'strategy__name']


@admin.register(OptimizationResult)
class OptimizationResultAdmin(admin.ModelAdmin):
    list_display = ['optimization_run', 'sharpe', 'total_return', 'max_drawdown', 'win_rate', 'total_trades']


@admin.register(MonteCarloRun)
class MonteCarloRunAdmin(admin.ModelAdmin):
    list_display = ['backtest_run', 'num_simulations', 'confidence_level', 'status', 'completed_at']
    list_filter = ['status']


@admin.register(MonteCarloResult)
class MonteCarloResultAdmin(admin.ModelAdmin):
    list_display = ['monte_carlo_run', 'metric_name', 'mean_value', 'median_value', 'percentile_5', 'percentile_95']
