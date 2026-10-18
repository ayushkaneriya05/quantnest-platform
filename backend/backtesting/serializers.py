"""
Serializers for the backtesting app.
"""
from decimal import Decimal
import uuid
from django.db import transaction
from rest_framework import serializers
from common.costs import get_charges_breakdown
from .models import (
    BacktestRun, BacktestTrade, BacktestMetrics, EquityCurvePoint,
    MonteCarloRun, MonteCarloResult
)


class ChargeProfileSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


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
    charge_profile_detail = ChargeProfileSummarySerializer(source='charge_profile', read_only=True)
    estimate_token = serializers.CharField(write_only=True, required=False, max_length=32768)

    class Meta:
        model = BacktestRun
        fields = [
            'id', 'name', 'strategy', 'strategy_name', 'strategy_version', 'start_date', 'end_date',
            'initial_capital', 'slippage_pct',
            'charge_profile', 'charge_profile_detail', 'include_charges',
            'parameters', 'config_snapshot', 'data_quality', 'diagnostics', 'estimate_token',
            'status', 'progress_pct', 'progress_message', 'error_message', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'progress_pct', 'progress_message', 'data_quality', 'diagnostics', 'config_snapshot', 'strategy_version', 'started_at', 'completed_at']

    def validate(self, attrs):
        """Validate creation inputs; saved backtests have no edit endpoint."""
        initial_capital = attrs.get("initial_capital")
        slippage_pct = attrs.get("slippage_pct")
        charge_profile = attrs.get("charge_profile")
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        if initial_capital is not None and initial_capital <= 0:
            raise serializers.ValidationError({"initial_capital": "Initial capital must be greater than zero."})
        if slippage_pct is not None and slippage_pct < 0:
            raise serializers.ValidationError({"slippage_pct": "Slippage cannot be negative."})
        if attrs.get("include_charges", True) and charge_profile is None:
            raise serializers.ValidationError({"charge_profile": "Select a charge profile or turn off charges."})
        request = self.context.get("request")
        if charge_profile is not None and request and charge_profile.user_id != request.user.id:
            raise serializers.ValidationError({"charge_profile": "Select a charge profile owned by your account."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from commercial.usage import reserve_usage
        from .services import backtest_configuration
        user = validated_data["user"]
        request = self.context.get("request")
        key = getattr(request, "headers", {}).get("Idempotency-Key") or f"backtest:{uuid.uuid4()}"
        token = validated_data.pop("estimate_token", "")
        config = backtest_configuration(BacktestRun(**validated_data))
        payload = {**{key: getattr(value, "pk", value) for key, value in validated_data.items()}, "config": config}
        run = super().create(validated_data)
        reserve_usage(user, "backtest_credits", key, payload, resource=run, estimate_token=token)
        return run


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
        return get_charges_breakdown([obj.charges_json])


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
        return get_charges_breakdown(trade.charges_json for trade in obj.run.trades.all())


class EquityCurvePointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquityCurvePoint
        fields = ['id', 'timestamp', 'equity_value', 'drawdown_pct']


class BacktestRunDetailSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    metrics = BacktestMetricsSerializer(read_only=True)
    trades_count = serializers.IntegerField(source='trades.count', read_only=True)
    charge_profile_detail = ChargeProfileSummarySerializer(source='charge_profile', read_only=True)

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


class MonteCarloRunSerializer(serializers.ModelSerializer):
    num_simulations = serializers.IntegerField(min_value=100)
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
