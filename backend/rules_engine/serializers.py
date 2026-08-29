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
            'start_time', 'end_time', 'candle_timeframe',
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
        from common.enums import OperandType, ComparisonOperator

        op_a_type = attrs.get('operand_a_type')
        op_b_type = attrs.get('operand_b_type')
        comparison = attrs.get('comparison')

        # Validate operand_a_type is set
        if not op_a_type:
            raise serializers.ValidationError({"operand_a_type": "Operand A type is required."})

        # Validate operand types are valid enum values
        valid_operands = {choice[0] for choice in OperandType.choices}
        if op_a_type and op_a_type not in valid_operands:
            raise serializers.ValidationError({"operand_a_type": f"Invalid operand type: {op_a_type}"})
        if op_b_type and op_b_type not in valid_operands:
            raise serializers.ValidationError({"operand_b_type": f"Invalid operand type: {op_b_type}"})

        # Validate comparison operator
        if comparison:
            valid_comparisons = {choice[0] for choice in ComparisonOperator.choices}
            if comparison not in valid_comparisons:
                raise serializers.ValidationError({"comparison": f"Invalid comparison operator: {comparison}"})

        # CONSTANT operand requires a 'value' param
        op_a_params = attrs.get('operand_a_params') or {}
        op_b_params = attrs.get('operand_b_params') or {}

        if op_a_type == OperandType.CONSTANT and 'value' not in op_a_params:
            raise serializers.ValidationError({"operand_a_params": "CONSTANT operand requires a 'value' parameter."})
        if op_b_type == OperandType.CONSTANT and 'value' not in op_b_params:
            raise serializers.ValidationError({"operand_b_params": "CONSTANT operand requires a 'value' parameter."})

        # CANDLE_PATTERN requires a 'pattern' param
        if op_a_type == OperandType.CANDLE_PATTERN and 'pattern' not in op_a_params:
            raise serializers.ValidationError({"operand_a_params": "CANDLE_PATTERN operand requires a 'pattern' parameter."})

        # Crosses operators need a comparison target (operand B)
        crosses_operators = {ComparisonOperator.CROSSES_ABOVE, ComparisonOperator.CROSSES_BELOW}
        if comparison in crosses_operators and not op_b_type:
            raise serializers.ValidationError({"operand_b_type": "Crosses comparison requires an Operand B."})

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
