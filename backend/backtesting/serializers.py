"""
Serializers for the backtesting app.
"""
from rest_framework import serializers
from .models import (
    BacktestRun, BacktestTrade, BacktestMetrics, EquityCurvePoint,
    OptimizationRun, OptimizationResult, MonteCarloRun, MonteCarloResult
)


class BacktestRunListSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_capital', 'status', 'progress_pct', 'created_at'
        ]


class BacktestRunSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct', 'brokerage_per_trade', 'brokerage_pct',
            'data_resolution', 'config_snapshot', 'status', 'progress_pct',
            'error_message', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'progress_pct', 'started_at', 'completed_at']


class BacktestTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    
    class Meta:
        model = BacktestTrade
        fields = [
            'id', 'instrument', 'instrument_symbol', 'side', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity', 'gross_pnl', 'brokerage',
            'slippage', 'net_pnl', 'pnl_pct', 'holding_duration_minutes',
            'exit_reason', 'entry_rule', 'exit_rule'
        ]


class BacktestMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestMetrics
        fields = [
            'id', 'total_trades', 'winning_trades', 'losing_trades', 'breakeven_trades',
            'win_rate', 'avg_win', 'avg_loss', 'largest_win', 'largest_loss', 'avg_trade_pnl',
            'avg_holding_time_minutes', 'profit_factor', 'expectancy', 'payoff_ratio',
            'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
            'max_drawdown_pct', 'max_drawdown_amount', 'max_drawdown_duration_days',
            'recovery_factor', 'final_capital', 'total_return_pct', 'cagr', 'volatility_pct',
            'total_brokerage', 'total_slippage'
        ]


class EquityCurvePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquityCurvePoint
        fields = ['id', 'timestamp', 'equity_value', 'drawdown_pct']


class BacktestRunDetailSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    metrics = BacktestMetricsSerializer(read_only=True)
    trades_count = serializers.IntegerField(source='trades.count', read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct', 'brokerage_per_trade', 'brokerage_pct',
            'data_resolution', 'config_snapshot', 'status', 'progress_pct',
            'error_message', 'started_at', 'completed_at', 'created_at',
            'metrics', 'trades_count'
        ]


class OptimizationRunSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    progress_pct = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = OptimizationRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_capital', 'parameters_to_optimize', 'optimization_metric',
            'total_combinations', 'completed_combinations', 'progress_pct',
            'best_params', 'best_metric_value', 'status', 'started_at', 'completed_at'
        ]
        read_only_fields = ['user', 'status', 'started_at', 'completed_at']


class OptimizationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationResult
        fields = ['id', 'params', 'sharpe', 'total_return', 'max_drawdown', 'win_rate', 'profit_factor', 'total_trades']


class MonteCarloRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonteCarloRun
        fields = ['id', 'backtest_run', 'num_simulations', 'confidence_level', 'status', 'completed_at']


class MonteCarloResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonteCarloResult
        fields = [
            'id', 'metric_name', 'mean_value', 'median_value', 'std_dev',
            'percentile_5', 'percentile_95', 'worst_case', 'best_case'
        ]
