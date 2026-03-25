"""
Serializers for the risk_management app.
"""
from rest_framework import serializers
from .models import (
    PositionSizingRule, PortfolioRiskProfile, TradeHaltCondition,
    StrategyAutoDisable, RiskViolation
)


class PositionSizingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionSizingRule
        fields = [
            'id', 'strategy', 'sizing_method', 'fixed_quantity', 'capital_percentage',
            'risk_per_trade_amount', 'risk_per_trade_percentage',
            'max_daily_trades', 'max_open_positions',
        ]


class PortfolioRiskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioRiskProfile
        fields = [
            'id', 'max_daily_loss_amount', 'max_daily_loss_percentage', 'max_daily_trades',
            'max_open_positions', 'max_exposure_percentage', 'max_per_strategy_allocation',
            'max_per_instrument_exposure', 'max_drawdown_percentage',
            'trailing_drawdown_reset', 'alert_on_breach', 'halt_on_breach'
        ]
        read_only_fields = ['user']


class TradeHaltConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeHaltCondition
        fields = [
            'id', 'name', 'description', 'condition_type',
            'threshold_value', 'threshold_count', 'halt_duration_minutes',
            'close_open_positions', 'send_notification', 'is_active'
        ]
        read_only_fields = ['user']


class StrategyAutoDisableSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyAutoDisable
        fields = [
            'id', 'strategy', 'name', 'trigger_type', 'threshold_value', 'threshold_count',
            'auto_reenable', 'cooldown_hours', 'require_manual_review', 'is_active'
        ]


class RiskViolationSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    
    class Meta:
        model = RiskViolation
        fields = [
            'id', 'strategy', 'strategy_name', 'violation_type', 'severity',
            'message', 'threshold_value', 'actual_value', 'action_taken',
            'is_resolved', 'resolved_at', 'resolution_notes', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']
