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
    charge_profile_detail = serializers.SerializerMethodField()

    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'strategy_version', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct', 'brokerage_per_trade', 'brokerage_pct',
            'fill_model', 'charge_profile', 'charge_profile_detail', 'include_charges',
            'parameters', 'config_snapshot', 'risk_profile_snapshot',
            'status', 'progress_pct', 'error_message', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'progress_pct', 'started_at', 'completed_at']

    def get_charge_profile_detail(self, obj):
        if obj.charge_profile:
            return {
                'id': obj.charge_profile.id,
                'name': getattr(obj.charge_profile, 'name', str(obj.charge_profile))
            }
        return None


class BacktestTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    charges_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = BacktestTrade
        fields = [
            'id', 'instrument', 'instrument_symbol', 'side', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity', 'gross_pnl', 'brokerage',
            'slippage', 'net_pnl', 'charges_json', 'charges_breakdown', 'pnl_pct', 'mae', 'mfe', 'holding_duration_minutes',
            'exit_reason', 'entry_rule', 'exit_rule'
        ]

    def get_charges_breakdown(self, obj):
        totals = {
            'brokerage': 0.0,
            'stt': 0.0,
            'exchange_txn': 0.0,
            'sebi': 0.0,
            'stamp_duty': 0.0,
            'gst': 0.0,
            'total': 0.0,
        }
        charges = obj.charges_json or {}
        totals['total'] = float(charges.get('total_charges', 0) or 0)
        for leg_name in ('entry_charges', 'exit_charges'):
            leg = charges.get(leg_name) or {}
            totals['brokerage'] += float(leg.get('brokerage', 0) or 0)
            totals['stt'] += float(leg.get('stt', 0) or 0)
            totals['exchange_txn'] += float(leg.get('exchange_charges', leg.get('exchange', 0)) or 0)
            totals['sebi'] += float(leg.get('sebi_fee', leg.get('sebi', 0)) or 0)
            totals['stamp_duty'] += float(leg.get('stamp_duty', 0) or 0)
            totals['gst'] += float(leg.get('gst', 0) or 0)
        return {key: round(value, 2) for key, value in totals.items()}


class BacktestMetricsSerializer(serializers.ModelSerializer):
    charges_breakdown = serializers.SerializerMethodField()

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
            'total_brokerage', 'total_slippage', 'total_charges', 'charges_breakdown', 'avg_mae', 'avg_mfe',
            'trade_efficiency', 'monthly_returns_json'
        ]

    def get_charges_breakdown(self, obj):
        totals = {
            'brokerage': 0.0,
            'stt': 0.0,
            'exchange_charges': 0.0,
            'exchange_txn': 0.0,
            'sebi_fee': 0.0,
            'sebi': 0.0,
            'stamp_duty': 0.0,
            'gst': 0.0,
            'total': 0.0,
        }
        for trade in obj.run.trades.all():
            charges = trade.charges_json or {}
            totals['total'] += float(charges.get('total_charges', 0) or 0)
            for leg_name in ('entry_charges', 'exit_charges'):
                leg = charges.get(leg_name) or {}
                totals['brokerage'] += float(leg.get('brokerage', 0) or 0)
                totals['stt'] += float(leg.get('stt', 0) or 0)
                exchange = float(leg.get('exchange_charges', leg.get('exchange', 0)) or 0)
                sebi = float(leg.get('sebi_fee', leg.get('sebi', 0)) or 0)
                totals['exchange_charges'] += exchange
                totals['exchange_txn'] += exchange
                totals['sebi_fee'] += sebi
                totals['sebi'] += sebi
                totals['stamp_duty'] += float(leg.get('stamp_duty', 0) or 0)
                totals['gst'] += float(leg.get('gst', 0) or 0)
        return {key: round(value, 2) for key, value in totals.items()}


class EquityCurvePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquityCurvePoint
        fields = ['id', 'timestamp', 'equity_value', 'drawdown_pct']


class BacktestRunDetailSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    metrics = BacktestMetricsSerializer(read_only=True)
    trades_count = serializers.IntegerField(source='trades.count', read_only=True)
    charge_profile_detail = serializers.SerializerMethodField()

    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct', 'brokerage_per_trade', 'brokerage_pct',
            'fill_model', 'charge_profile', 'charge_profile_detail', 'include_charges',
            'config_snapshot', 'status', 'progress_pct',
            'error_message', 'started_at', 'completed_at', 'created_at',
            'metrics', 'trades_count'
        ]

    def get_charge_profile_detail(self, obj):
        if obj.charge_profile:
            return {
                'id': obj.charge_profile.id,
                'name': getattr(obj.charge_profile, 'name', str(obj.charge_profile))
            }
        return None


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
