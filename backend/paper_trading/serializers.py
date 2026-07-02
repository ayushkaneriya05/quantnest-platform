from decimal import Decimal
from rest_framework import serializers
from common.enums import ProductType
from .models import (
    PaperAccount, PaperPosition, PaperOrder, PaperTrade,
    Portfolio, CapitalAllocation, FundTransaction,
    ExposureSnapshot, DailyPerformance
)


class PortfolioSerializer(serializers.ModelSerializer):
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    current_drawdown = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    allocations = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'name', 'initial_capital', 'current_capital', 'invested_value',
            'realized_pnl', 'unrealized_pnl', 'peak_value', 'peak_date',
            'today_pnl', 'today_trades',
            'total_value', 'current_drawdown', 'is_active', 'allocations'
        ]
        read_only_fields = ['user']

    def get_allocations(self, obj):
        allocations = obj.allocations.select_related("strategy").all()
        return [
            {
                "id": allocation.id,
                "strategy": allocation.strategy_id,
                "strategy_name": allocation.strategy.name,
                "allocated_amount": allocation.allocated_amount,
                "allocated_percentage": allocation.allocated_percentage,
                "utilized_amount": allocation.utilized_amount,
                "total_pnl": allocation.total_pnl,
                "today_pnl": allocation.today_pnl,
                "is_active": allocation.is_active,
            }
            for allocation in allocations
        ]


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

    def _get_effective_amount(self, alloc, portfolio_equity):
        if alloc.allocation_type == 'PERCENTAGE':
            return (Decimal(str(alloc.allocated_percentage or 0)) / 100) * portfolio_equity
        return Decimal(str(alloc.allocated_amount or 0))

    def validate_allocation_type(self, value):
        if value not in ['FIXED', 'PERCENTAGE']:
            raise serializers.ValidationError(f"Invalid allocation type: {value}")
        return value

    def validate(self, attrs):
        portfolio = attrs.get('portfolio') or (self.instance.portfolio if self.instance else None)
        if not portfolio:
            raise serializers.ValidationError("Portfolio is required")

        strategy = attrs.get('strategy')
        if not strategy:
            raise serializers.ValidationError("Strategy is required")

        portfolio_equity = portfolio.total_value
        if portfolio_equity <= 0:
            raise serializers.ValidationError("Portfolio has no capital to allocate")

        alloc_type = attrs.get('allocation_type', getattr(self.instance, 'allocation_type', 'FIXED'))

        if alloc_type == 'PERCENTAGE':
            pct = Decimal(str(attrs.get('allocated_percentage') or 0))
            if pct <= 0 or pct > 100:
                raise serializers.ValidationError("Percentage must be between 1 and 100")
            attrs['allocated_amount'] = 0
            this_amount = (pct / 100) * portfolio_equity
        else:
            amt = Decimal(str(attrs.get('allocated_amount') or 0))
            if amt <= 0:
                raise serializers.ValidationError("Amount must be greater than 0")
            attrs['allocated_percentage'] = 0
            this_amount = amt

        others = CapitalAllocation.objects.filter(portfolio=portfolio)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)

        already_allocated = sum(self._get_effective_amount(a, portfolio_equity) for a in others)

        if already_allocated + this_amount > portfolio_equity:
            remaining = portfolio_equity - already_allocated
            raise serializers.ValidationError(
                f"Allocation exceeds available capital. Portfolio equity: ₹{portfolio_equity:,.0f}, "
                f"Already allocated: ₹{already_allocated:,.0f}, Remaining: ₹{remaining:,.0f}"
            )

        if alloc_type == 'PERCENTAGE':
            other_pct = sum(
                Decimal(str(a.allocated_percentage or 0))
                for a in others if a.allocation_type == 'PERCENTAGE'
            )
            total_pct = other_pct + pct
            if total_pct > 100:
                raise serializers.ValidationError(
                    f"Total percentage allocation ({total_pct}%) exceeds 100%. "
                    f"Already allocated: {other_pct}%, Remaining: {100 - other_pct}%"
                )

        return attrs


class FundTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundTransaction
        fields = [
            'id', 'portfolio', 'transaction_type', 'amount',
            'balance_before', 'balance_after', 'notes',
            'created_at'
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
            'max_exposure', 'avg_exposure'
        ]


class PaperAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperAccount
        fields = [
            'id', 'name', 'initial_balance', 'current_balance',
            'total_pnl', 'realized_pnl', 'unrealized_pnl',
            'today_pnl', 'today_trades', 'margin_used', 'margin_available',
            'is_active', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


class PaperPositionSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    invested_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = PaperPosition
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'side', 'quantity', 'avg_price', 'current_price',
            'unrealized_pnl', 'realized_pnl',
            'margin_blocked', 'current_value', 'invested_value', 'opened_at'
        ]


class PaperOrderSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_filled = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaperOrder
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'order_type', 'product_type', 'side', 'quantity', 'price', 'trigger_price',
            'filled_quantity', 'avg_fill_price',
            'status', 'rejection_reason', 'order_tag',
            'is_filled', 'is_pending', 'placed_at', 'executed_at'
        ]
        read_only_fields = ['filled_quantity', 'avg_fill_price', 'status', 'placed_at', 'executed_at', 'account', 'strategy', 'instrument', 'order_type', 'product_type', 'side', 'quantity', 'price', 'trigger_price']


class PaperTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_winner = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaperTrade
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'side', 'quantity', 'entry_price', 'entry_time',
            'exit_price', 'exit_time', 'exit_reason',
            'gross_pnl', 'net_pnl', 'pnl_pct',
            'holding_duration_seconds', 'is_winner'
        ]
