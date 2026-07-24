"""
Serializers for the rules_engine app.
"""
from rest_framework import serializers
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule


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
            'avoid_rbi_policy', 'custom_avoid_dates'
        ]


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = [
            'id', 'rule_group', 'operand_a_type', 'operand_a_params', 'operand_a_timeframe',
            'comparison', 'operand_b_type', 'operand_b_params', 'operand_b_timeframe',
            'is_active'
        ]

    def validate(self, attrs):
        # Add any advanced validation here if needed, for now just accept whatever the user builds
        # The executor will handle invalid configurations at runtime if they pass schema checks
        return attrs


class RuleGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleGroup
        fields = [
            'id', 'strategy', 'name', 'rule_type', 'logical_operator',
            'priority', 'action', 'action_params'
        ]
        read_only_fields = ['id']


class RuleGroupSerializer(serializers.ModelSerializer):
    rules = RuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = RuleGroup
        fields = [
            'id', 'strategy', 'name', 'rule_type', 'logical_operator',
            'priority', 'action', 'action_params',
            'is_active', 'rules'
        ]
