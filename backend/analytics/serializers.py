from rest_framework import serializers

from strategies.models import Strategy

from .models import DailyReport, PerformanceSnapshot, StrategyComparison


class PerformanceSnapshotSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = PerformanceSnapshot
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "date",
            "daily_pnl",
            "cumulative_pnl",
            "trades_count",
            "winning_trades",
            "win_rate",
            "avg_trade_pnl",
            "max_drawdown_pct",
            "sharpe_ratio_30d",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DailyReportSerializer(serializers.ModelSerializer):
    best_strategy_name = serializers.CharField(source="best_strategy.name", read_only=True)
    worst_strategy_name = serializers.CharField(source="worst_strategy.name", read_only=True)

    class Meta:
        model = DailyReport
        fields = [
            "id",
            "date",
            "total_pnl",
            "realized_pnl",
            "unrealized_pnl",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "best_trade",
            "worst_trade",
            "best_strategy",
            "best_strategy_name",
            "worst_strategy",
            "worst_strategy_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StrategyComparisonSerializer(serializers.ModelSerializer):
    strategies = serializers.PrimaryKeyRelatedField(queryset=Strategy.objects.all(), many=True)
    strategy_names = serializers.SerializerMethodField()

    class Meta:
        model = StrategyComparison
        fields = ["id", "strategies", "strategy_names", "start_date", "end_date", "comparison_data", "created_at", "updated_at"]
        read_only_fields = ["comparison_data", "created_at", "updated_at"]

    def get_strategy_names(self, obj):
        return [strategy.name for strategy in obj.strategies.all()]
