"""
Serializers for the risk_management app.
"""
from rest_framework import serializers
from common.enums import QuantityType, AutoDisableTriggerType
from .models import (
    PositionSizingRule, PortfolioRiskProfile,
    StrategyAutoDisable, RiskViolation
)


class PositionSizingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionSizingRule
        fields = [
            'id', 'strategy', 'sizing_method', 'fixed_quantity', 'capital_percentage',
            'risk_per_trade_amount', 'risk_per_trade_percentage',
            'loss_recovery_mode', 'loss_recovery_multiplier',
            'max_daily_trades', 'max_open_positions',
        ]

    def validate(self, attrs):
        method = attrs.get('sizing_method', getattr(self.instance, 'sizing_method', None))
        fixed_quantity = attrs.get('fixed_quantity', getattr(self.instance, 'fixed_quantity', None))
        capital_percentage = attrs.get('capital_percentage', getattr(self.instance, 'capital_percentage', None))
        risk_amount = attrs.get('risk_per_trade_amount', getattr(self.instance, 'risk_per_trade_amount', None))
        risk_percentage = attrs.get('risk_per_trade_percentage', getattr(self.instance, 'risk_per_trade_percentage', None))
        max_daily = attrs.get('max_daily_trades', getattr(self.instance, 'max_daily_trades', None))
        max_open = attrs.get('max_open_positions', getattr(self.instance, 'max_open_positions', None))

        if method == QuantityType.FIXED and (fixed_quantity is None or fixed_quantity < 1):
            raise serializers.ValidationError({'fixed_quantity': 'Fixed quantity must be at least 1.'})
        if method == QuantityType.CAPITAL_BASED and (capital_percentage is None or capital_percentage <= 0 or capital_percentage > 100):
            raise serializers.ValidationError({'capital_percentage': 'Capital percentage must be between 0 and 100.'})
        if method == QuantityType.RISK_FIXED and (risk_amount is None or risk_amount <= 0):
            raise serializers.ValidationError({'risk_per_trade_amount': 'Risk amount must be greater than zero.'})
        if method == QuantityType.RISK_PERCENTAGE and (risk_percentage is None or risk_percentage <= 0 or risk_percentage > 10):
            raise serializers.ValidationError({'risk_per_trade_percentage': 'Risk percentage must be between 0 and 10.'})
        if max_daily is None or max_daily < 1:
            raise serializers.ValidationError({'max_daily_trades': 'Max daily trades must be at least 1.'})
        if max_open is None or max_open < 1:
            raise serializers.ValidationError({'max_open_positions': 'Max open positions must be at least 1.'})
        return attrs


class PortfolioRiskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioRiskProfile
        fields = [
            'id', 'max_daily_loss_amount', 'max_daily_loss_percentage',
            'max_daily_profit_amount', 'max_daily_profit_percentage',
            'max_exposure_percentage', 'max_per_instrument_exposure',
            'max_drawdown_percentage', 'alert_on_breach'
        ]
        read_only_fields = ['user']

    def validate(self, attrs):
        percentage_fields = [
            'max_daily_loss_percentage',
            'max_exposure_percentage',
            'max_per_instrument_exposure',
            'max_drawdown_percentage',
        ]
        for field in percentage_fields:
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is not None and (value <= 0 or value > 100):
                raise serializers.ValidationError({field: 'Percentage must be between 0 and 100.'})

        max_loss_amount = attrs.get('max_daily_loss_amount', getattr(self.instance, 'max_daily_loss_amount', None))
        if max_loss_amount is not None and max_loss_amount < 0:
            raise serializers.ValidationError({'max_daily_loss_amount': 'Daily loss amount cannot be negative.'})
        return attrs


class StrategyAutoDisableSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyAutoDisable
        fields = [
            'id', 'strategy', 'name', 'trigger_type', 'threshold_value', 'threshold_count',
            'auto_reenable', 'cooldown_hours', 'require_manual_review', 'is_active'
        ]

    def validate(self, attrs):
        trigger_type = attrs.get('trigger_type', getattr(self.instance, 'trigger_type', None))
        threshold_value = attrs.get('threshold_value', getattr(self.instance, 'threshold_value', None))
        threshold_count = attrs.get('threshold_count', getattr(self.instance, 'threshold_count', None))
        cooldown_hours = attrs.get('cooldown_hours', getattr(self.instance, 'cooldown_hours', None))

        if trigger_type == AutoDisableTriggerType.CONSECUTIVE_LOSSES:
            if threshold_count is None or threshold_count < 1:
                raise serializers.ValidationError({'threshold_count': 'Consecutive-loss trigger requires a count of at least 1.'})
        elif threshold_value is None or threshold_value <= 0:
            raise serializers.ValidationError({'threshold_value': 'This trigger requires a threshold greater than zero.'})

        if cooldown_hours is not None and cooldown_hours < 0:
            raise serializers.ValidationError({'cooldown_hours': 'Cooldown cannot be negative.'})
        return attrs


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
