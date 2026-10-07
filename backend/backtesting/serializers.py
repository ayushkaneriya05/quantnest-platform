"""
Serializers for the backtesting app.
"""
from decimal import Decimal
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
            'initial_capital', 'status', 'progress_pct', 'progress_message', 'created_at'
        ]


class BacktestRunSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    charge_profile_detail = serializers.SerializerMethodField()

    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'strategy_version', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct',
            'charge_profile', 'charge_profile_detail', 'include_charges',
            'parameters', 'config_snapshot', 'data_quality', 'diagnostics',
            'status', 'progress_pct', 'progress_message', 'error_message', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'progress_pct', 'progress_message', 'data_quality', 'diagnostics', 'config_snapshot', 'strategy_version', 'started_at', 'completed_at']

    def get_charge_profile_detail(self, obj):
        if obj.charge_profile:
            return {
                'id': obj.charge_profile.id,
                'name': getattr(obj.charge_profile, 'name', str(obj.charge_profile))
            }
        return None

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        initial_capital = attrs.get("initial_capital", getattr(self.instance, "initial_capital", None))
        slippage_pct = attrs.get("slippage_pct", getattr(self.instance, "slippage_pct", None))
        include_charges = attrs.get("include_charges", getattr(self.instance, "include_charges", True))
        charge_profile = attrs.get("charge_profile", getattr(self.instance, "charge_profile", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        if initial_capital is not None and initial_capital <= 0:
            raise serializers.ValidationError({"initial_capital": "Initial capital must be greater than zero."})
        if slippage_pct is not None and slippage_pct < 0:
            raise serializers.ValidationError({"slippage_pct": "Slippage cannot be negative."})
        if include_charges and charge_profile is None:
            raise serializers.ValidationError({"charge_profile": "Select a charge profile or turn off charges."})
        request = self.context.get("request")
        if charge_profile is not None and request and charge_profile.user_id != request.user.id:
            raise serializers.ValidationError({"charge_profile": "Select a charge profile owned by your account."})
        return attrs


class BacktestTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    charges_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = BacktestTrade
        fields = [
            'id', 'instrument', 'instrument_symbol', 'side', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity', 'gross_pnl', 'brokerage',
            'slippage', 'net_pnl', 'charges_json', 'charges_breakdown', 'pnl_pct', 'mae', 'mfe', 'holding_duration_minutes',
            'exit_reason'
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
            'trade_efficiency', 'monthly_returns_json', 'instrument_breakdown_json'
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
        for trade in obj.run.trades.all():
            charges = trade.charges_json or {}
            totals['total'] += float(charges.get('total_charges', 0) or 0)
            for leg_name in ('entry_charges', 'exit_charges'):
                leg = charges.get(leg_name) or {}
                totals['brokerage'] += float(leg.get('brokerage', 0) or 0)
                totals['stt'] += float(leg.get('stt', 0) or 0)
                exchange = float(leg.get('exchange_charges', leg.get('exchange', 0)) or 0)
                sebi = float(leg.get('sebi_fee', leg.get('sebi', 0)) or 0)
                totals['exchange_txn'] += exchange
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
            'initial_capital', 'slippage_pct',
            'charge_profile', 'charge_profile_detail', 'include_charges',
            'config_snapshot', 'data_quality', 'diagnostics', 'status', 'progress_pct', 'progress_message',
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
    num_simulations = serializers.IntegerField(min_value=100, max_value=10000)
    confidence_level = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=Decimal("0.90"), max_value=Decimal("0.99"),
    )

    class Meta:
        model = MonteCarloRun
        fields = [
            'id', 'backtest_run', 'num_simulations', 'confidence_level', 'status',
            'error_message', 'completed_at', 'equity_distribution_json',
        ]
        read_only_fields = ['status', 'error_message', 'completed_at', 'equity_distribution_json']

    def validate_backtest_run(self, backtest_run):
        request = self.context.get('request')
        if request and backtest_run.user_id != request.user.id:
            raise serializers.ValidationError("Select a backtest owned by your account.")
        if backtest_run.status != 'COMPLETED':
            raise serializers.ValidationError("Monte Carlo requires a completed backtest.")
        if not backtest_run.trades.exists():
            raise serializers.ValidationError("The selected backtest has no trades to simulate.")
        return backtest_run


class MonteCarloResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonteCarloResult
        fields = [
            'id', 'metric_name', 'valid_simulations', 'mean_value', 'median_value', 'std_dev',
            'lower_outcome_bound', 'upper_outcome_bound', 'worst_case', 'best_case'
        ]
