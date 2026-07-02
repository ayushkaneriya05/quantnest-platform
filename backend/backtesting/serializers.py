"""
Serializers for the backtesting app.
"""
from rest_framework import serializers
from .models import (
    BacktestRun, BacktestTrade, BacktestMetrics, EquityCurvePoint,
    MonteCarloRun, MonteCarloResult
)


class BacktestRunListSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'strategy_version', 'start_date', 'end_date',
            'initial_capital', 'status', 'progress_pct', 'created_at'
        ]


class BacktestRunSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'strategy_version', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct', 'brokerage_per_trade', 'brokerage_pct',
            'parameters', 'config_snapshot', 'risk_profile_snapshot',
            'status', 'progress_pct', 'error_message', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'progress_pct', 'started_at', 'completed_at']


class BacktestTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    
    class Meta:
        model = BacktestTrade
        fields = [
            'id', 'instrument', 'instrument_symbol', 'side', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity', 'gross_pnl', 'brokerage',
            'slippage', 'net_pnl', 'pnl_pct', 'mae', 'mfe', 'holding_duration_minutes',
            'exit_reason', 'entry_rule', 'exit_rule'
        ]


class BacktestMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestMetrics
        fields = [
            'id', 'total_trades', 'winning_trades', 'losing_trades', 'breakeven_trades',
            'max_consecutive_wins', 'max_consecutive_losses',
            'win_rate', 'avg_win', 'avg_loss', 'largest_win', 'largest_loss', 'avg_trade_pnl',
            'avg_holding_time_minutes', 'avg_winning_hold_time', 'avg_losing_hold_time',
            'profit_factor', 'expectancy', 'payoff_ratio',
            'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
            'max_drawdown_pct', 'max_drawdown_amount', 'max_drawdown_duration_days',
            'recovery_factor', 'final_capital', 'total_return_pct', 'cagr', 'volatility_pct',
            'total_brokerage', 'total_slippage', 'avg_mae', 'avg_mfe',
            'trade_efficiency', 'monthly_returns_json'
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
            'config_snapshot', 'status', 'progress_pct',
            'error_message', 'started_at', 'completed_at', 'created_at',
            'metrics', 'trades_count'
        ]


class MonteCarloRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonteCarloRun
        fields = ['id', 'backtest_run', 'num_simulations', 'confidence_level', 'status', 'completed_at', 'equity_distribution_json']


class MonteCarloResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonteCarloResult
        fields = [
            'id', 'metric_name', 'mean_value', 'median_value', 'std_dev',
            'percentile_5', 'percentile_95', 'worst_case', 'best_case'
        ]
