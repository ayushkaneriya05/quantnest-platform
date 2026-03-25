"""
Serializers for the portfolio app.
"""
from rest_framework import serializers
from .models import (
    Portfolio, CapitalAllocation, FundTransaction,
    ExposureSnapshot, DailyPerformance
)


class PortfolioSerializer(serializers.ModelSerializer):
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    current_drawdown = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'name', 'initial_capital', 'current_capital', 'invested_value',
            'realized_pnl', 'unrealized_pnl', 'peak_value', 'peak_date',
            'today_pnl', 'today_trades', 'broker_synced', 'last_broker_sync',
            'total_value', 'current_drawdown', 'is_active'
        ]
        read_only_fields = ['user']


class CapitalAllocationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    available_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = CapitalAllocation
        fields = [
            'id', 'portfolio', 'strategy', 'strategy_name', 'allocation_type',
            'allocated_amount', 'allocated_percentage', 'utilized_amount',
            'available_amount', 'total_pnl', 'today_pnl', 'auto_rebalance',
            'rebalance_frequency', 'last_rebalance', 'is_active'
        ]

    def _get_effective_amount(self, alloc, capital):
        """Compute effective amount for an allocation."""
        if alloc.allocation_type == 'PERCENTAGE':
            return (float(alloc.allocated_percentage or 0) / 100) * capital
        return float(alloc.allocated_amount or 0)

    def validate(self, attrs):
        portfolio = attrs.get('portfolio') or (self.instance.portfolio if self.instance else None)
        if not portfolio:
            return attrs

        capital = float(portfolio.current_capital or 0)
        alloc_type = attrs.get('allocation_type', getattr(self.instance, 'allocation_type', 'FIXED'))

        # Compute this allocation's effective amount
        if alloc_type == 'PERCENTAGE':
            pct = float(attrs.get('allocated_percentage', 0))
            this_amount = (pct / 100) * capital
        else:
            this_amount = float(attrs.get('allocated_amount', 0))

        # Get all other allocations for this portfolio (exclude self if editing)
        others = CapitalAllocation.objects.filter(portfolio=portfolio)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)

        already_allocated = sum(self._get_effective_amount(a, capital) for a in others)

        if already_allocated + this_amount > capital:
            remaining = capital - already_allocated
            raise serializers.ValidationError(
                f"Total allocation exceeds portfolio capital (₹{capital:,.0f}). "
                f"Max remaining: ₹{remaining:,.0f}"
            )

        # Validate total percentage doesn't exceed 100%
        if alloc_type == 'PERCENTAGE':
            other_pct = sum(
                float(a.allocated_percentage or 0)
                for a in others if a.allocation_type == 'PERCENTAGE'
            )
            if other_pct + float(attrs.get('allocated_percentage', 0)) > 100:
                raise serializers.ValidationError(
                    f"Total percentage exceeds 100%. Already used: {other_pct}%"
                )

        return attrs


class FundTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundTransaction
        fields = [
            'id', 'portfolio', 'transaction_type', 'amount',
            'balance_before', 'balance_after', 'notes',
            'requires_approval', 'is_approved', 'approved_by', 'approved_at', 'created_at'
        ]
        read_only_fields = ['balance_before', 'balance_after', 'created_at']


class ExposureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExposureSnapshot
        fields = [
            'id', 'snapshot_time', 'total_exposure', 'exposure_percentage',
            'long_exposure', 'short_exposure', 'net_exposure',
            'exposure_by_asset_type', 'exposure_by_sector', 'exposure_by_strategy',
            'open_positions_count'
        ]


class DailyPerformanceSerializer(serializers.ModelSerializer):
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = DailyPerformance
        fields = [
            'id', 'date', 'opening_capital', 'closing_capital',
            'realized_pnl', 'unrealized_pnl', 'total_pnl', 'pnl_percentage',
            'trades_count', 'winning_trades', 'losing_trades', 'win_rate',
            'max_exposure', 'avg_exposure', 'brokerage_paid', 'taxes_paid'
        ]
