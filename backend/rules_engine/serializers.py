"""
Serializers for the rules_engine app.
"""
from rest_framework import serializers
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule, StopLossRule, TargetRule


class TimeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeRule
        fields = [
            'id', 'strategy', 'trading_days', 'market_session',
            'start_time', 'end_time', 'candle_timeframe', 'candle_completion_rule',
            'no_trade_windows', 'timezone'
        ]


class SpecialEventFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialEventFilter
        fields = [
            'id', 'strategy', 'avoid_earnings', 'avoid_news',
            'avoid_expiry_day', 'avoid_rbi_policy', 'custom_avoid_dates'
        ]


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = [
            'id', 'rule_group', 'category', 'indicator_type', 'price_action_type',
            'volume_condition_type', 'params', 'comparison', 'value', 'value2',
            'compare_to_indicator', 'compare_to_params', 'timeframe_override',
            'is_active'
        ]





class RuleGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleGroup
        fields = [
            'strategy', 'name', 'rule_type', 'logical_operator',
            'priority'
        ]


class StopLossRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopLossRule
        fields = [
            'id', 'rule_group', 'sl_type', 'fixed_points', 'fixed_percentage',
            'indicator_type', 'indicator_params',
            'operator', 'threshold_value', 'threshold_value2', 'compare_to_indicator', 'compare_to_params', 'timeframe_override',
            'candle_part', 'candle_offset', 'candle_lookback',
            'trailing_value',
            'time_minutes', 'emergency_loss_pct',
            'is_active'
        ]


class TargetRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetRule
        fields = [
            'id', 'rule_group', 'target_type', 'fixed_points', 'fixed_percentage',
            'risk_reward_ratio', 'indicator_type', 'indicator_params',
            'operator', 'threshold_value', 'threshold_value2', 'compare_to_indicator', 'compare_to_params', 'timeframe_override',
            'trailing_value',
            'time_exit_minutes', 'eod_squareoff_time', 'expiry_exit_minutes_before',
            'is_active'
        ]


class RuleGroupSerializer(serializers.ModelSerializer):
    rules = RuleSerializer(many=True, read_only=True)
    stop_loss_rules = StopLossRuleSerializer(many=True, read_only=True)
    target_rules = TargetRuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = RuleGroup
        fields = [
            'id', 'strategy', 'name', 'rule_type', 'logical_operator',
            'priority', 
            'is_active', 'rules', 'stop_loss_rules', 'target_rules'
        ]
