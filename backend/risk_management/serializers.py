"""
Serializers for the risk_management app.
"""
from rest_framework import serializers
from common.enums import QuantityType, AutoDisableTriggerType
from .models import PositionSizingRule, StrategyAutoDisable


class PositionSizingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionSizingRule
        fields = [
            'id', 'strategy', 'sizing_method', 'fixed_quantity', 'capital_percentage',
            'risk_per_trade_percentage',
        ]

    def validate(self, attrs):
        method = attrs.get('sizing_method', getattr(self.instance, 'sizing_method', None))
        fixed_quantity = attrs.get('fixed_quantity', getattr(self.instance, 'fixed_quantity', None))
        capital_percentage = attrs.get('capital_percentage', getattr(self.instance, 'capital_percentage', None))
        risk_percentage = attrs.get('risk_per_trade_percentage', getattr(self.instance, 'risk_per_trade_percentage', None))

        if method == QuantityType.FIXED and (fixed_quantity is None or fixed_quantity < 1):
            raise serializers.ValidationError({'fixed_quantity': 'Fixed quantity must be at least 1.'})
        if method == QuantityType.CAPITAL_BASED and (capital_percentage is None or capital_percentage <= 0 or capital_percentage > 100):
            raise serializers.ValidationError({'capital_percentage': 'Capital percentage must be between 0 and 100.'})
        if method == QuantityType.RISK_BASED and (risk_percentage is None or risk_percentage <= 0 or risk_percentage > 10):
            raise serializers.ValidationError({'risk_per_trade_percentage': 'Risk percentage must be between 0 and 10.'})
        
        return attrs


class StrategyAutoDisableSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyAutoDisable
        fields = [
            'id', 'strategy', 'name', 'trigger_type', 'threshold_value', 'threshold_count',
            'auto_reenable', 'cooldown_hours', 'is_active'
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
