from rest_framework import serializers
from common.costs import get_charges_breakdown
from .models import (
    PaperAccount, PaperPosition, PaperOrder, PaperTrade,
    Portfolio, FundTransaction,
    PaperTradingSession
)
from strategies.serializers import StrategyVersionListSerializer


class PortfolioSerializer(serializers.ModelSerializer):
    total_value = serializers.ReadOnlyField()
    invested_value = serializers.ReadOnlyField()
    allocated_capital = serializers.ReadOnlyField()
    realized_pnl = serializers.ReadOnlyField()
    unrealized_pnl = serializers.ReadOnlyField()
    today_pnl = serializers.ReadOnlyField()
    today_trades = serializers.ReadOnlyField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'name', 'initial_capital', 'current_capital', 'invested_value', 'allocated_capital',
            'realized_pnl', 'unrealized_pnl',
            'today_pnl', 'today_trades',
            'total_value', 'is_active'
        ]
        read_only_fields = ['user']

class FundTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundTransaction
        fields = [
            'id', 'portfolio', 'transaction_type', 'amount',
            'balance_before', 'balance_after', 'notes',
            'created_at'
        ]
        read_only_fields = ['balance_before', 'balance_after', 'created_at']


class PaperTradingSessionSerializer(serializers.ModelSerializer):
    applied_version = serializers.IntegerField(source='applied_version_id', read_only=True, allow_null=True)
    applied_at = serializers.DateTimeField(read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    name = serializers.CharField(source="account.name", read_only=True)
    strategy_status = serializers.CharField(source="strategy.status", read_only=True)
    paper_trading_enabled = serializers.BooleanField(source="strategy.paper_trading_enabled", read_only=True)
    deployed_version = StrategyVersionListSerializer(source="allocation.deployed_version", read_only=True)
    allocated_capital = serializers.ReadOnlyField(source="allocation.allocated_amount")
    available_capital = serializers.ReadOnlyField(source="account.annotated_available_capital")
    used_capital = serializers.ReadOnlyField(source="account.annotated_used_capital")
    balance = serializers.ReadOnlyField(source="account.current_balance")
    realized_pnl = serializers.ReadOnlyField(source="account.annotated_realized_pnl")
    trades_count = serializers.IntegerField(source="account.annotated_trade_count", read_only=True)
    open_positions = serializers.IntegerField(source="account.annotated_open_positions", read_only=True)
    charge_profile_name = serializers.SerializerMethodField()

    class Meta:
        model = PaperTradingSession
        fields = [
            'id', 'user', 'strategy', 'strategy_name', 'strategy_status', 'paper_trading_enabled',
            'name', 'allocation', 'account', 'deployed_version', 'applied_version', 'applied_at', 'allocated_capital',
            'available_capital', 'used_capital', 'balance', 'realized_pnl', 'open_positions',
            'slippage_pct', 'charge_profile', 'include_charges',
            'charge_profile_name',
            'status', 'started_at', 'ended_at', 'trades_count', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'slippage_pct', 'charge_profile', 'include_charges',
            'started_at', 'ended_at', 'created_at', 'updated_at'
        ]

    def get_charge_profile_name(self, obj):
        return (obj.charge_profile_snapshot or {}).get('name') or (
            obj.charge_profile.name if obj.charge_profile_id else None
        )


class PaperAccountSerializer(serializers.ModelSerializer):
    """Read-only ledger fields used by the session portfolio."""
    realized_pnl = serializers.ReadOnlyField(source="annotated_realized_pnl")
    today_trades = serializers.ReadOnlyField(source="annotated_today_trades")
    margin_used = serializers.ReadOnlyField(source="annotated_used_capital")
    margin_available = serializers.ReadOnlyField(source="annotated_available_capital")
    session_status = serializers.SerializerMethodField()
    session_id = serializers.SerializerMethodField()

    class Meta:
        model = PaperAccount
        fields = ["id", "name", "current_balance", "realized_pnl", "today_trades",
                  "margin_used", "margin_available", "session_status", "session_id"]
        read_only_fields = fields

    def get_session_status(self, obj):
        session = obj.sessions.first()
        return session.status if session else "STOPPED"

    def get_session_id(self, obj):
        session = obj.sessions.first()
        return session.pk if session else None


class PaperPositionSerializer(serializers.ModelSerializer):
    mark_at = serializers.DateTimeField(source="last_updated", read_only=True)
    qty_multiplier = serializers.DecimalField(source='instrument.qty_multiplier', max_digits=10, decimal_places=4, read_only=True)
    instrument_symbol = serializers.CharField(source='instrument.sym_ticker', read_only=True)
    instrument_sym_ticker = serializers.ReadOnlyField(source='instrument.sym_ticker')
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    invested_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    unrealized_pnl_pct = serializers.SerializerMethodField()
    
    class Meta:
        model = PaperPosition
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol', 'instrument_sym_ticker',
            'side', 'quantity', 'qty_multiplier', 'avg_price', 'current_price', 'mark_at',
            'unrealized_pnl',
            'margin_blocked', 'current_value', 'invested_value', 'unrealized_pnl_pct', 'opened_at'
        ]

    def get_unrealized_pnl_pct(self, obj):
        invested_value = obj.invested_value
        if not invested_value:
            return 0
        return (obj.unrealized_pnl / invested_value) * 100


class PaperOrderSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.sym_ticker', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_filled = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaperOrder
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'order_type', 'product_type', 'side', 'quantity', 'price', 'trigger_price',
            'filled_quantity', 'avg_fill_price',
            'slippage_pct_applied', 'slippage_amount',
            'status', 'rejection_reason', 'order_tag',
            'is_filled', 'is_pending', 'placed_at', 'executed_at'
        ]
        read_only_fields = [
            'filled_quantity', 'avg_fill_price', 'slippage_pct_applied', 'slippage_amount',
            'status', 'placed_at', 'executed_at', 'account', 'strategy', 'instrument',
            'order_type', 'product_type', 'side', 'quantity', 'price', 'trigger_price'
        ]


class PaperTradeSerializer(serializers.ModelSerializer):
    instrument_symbol = serializers.CharField(source='instrument.sym_ticker', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    is_winner = serializers.BooleanField(read_only=True)
    charges_breakdown = serializers.SerializerMethodField()
    
    class Meta:
        model = PaperTrade
        fields = [
            'id', 'account', 'strategy', 'strategy_name', 'instrument', 'instrument_symbol',
            'side', 'quantity', 'entry_price', 'entry_time',
            'exit_price', 'exit_time', 'exit_reason',
            'gross_pnl', 'net_pnl', 'pnl_pct', 'brokerage', 'taxes', 'charges_json', 'charges_breakdown',
            'holding_duration_seconds', 'is_winner'
        ]

    def get_charges_breakdown(self, obj):
        return get_charges_breakdown([obj.charges_json])
