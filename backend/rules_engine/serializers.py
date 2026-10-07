"""
Serializers for the rules_engine app.
"""
from rest_framework import serializers
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule
from .math_expressions import is_safe_arithmetic_expression
from common.enums import (
    OperandType, ComparisonOperator, CandlePatternType, CandleTimeframe, RuleType,
    get_math_expression_operand_types, get_operand_parameter_config,
    get_operand_parameter_defaults,
    OPERAND_PARAMETER_CONFIG,
)


def _normalize_and_validate_operand_params(operand_type, raw_params, field_name, math_variable_types=None):
    """Fill server-owned operand defaults and validate against the UI schema."""
    try:
        operand_type = OperandType(operand_type)
    except (TypeError, ValueError):
        return raw_params or {}

    if not isinstance(raw_params, dict):
        raise serializers.ValidationError({field_name: 'Parameters must be an object.'})

    params = {
        **get_operand_parameter_defaults(operand_type),
        **raw_params,
    }
    schema = get_operand_parameter_config(operand_type)

    def validate_fields(values, specs, prefix=''):
        normalized = dict(values)
        for spec in specs:
            key = spec['key']
            if key not in normalized:
                continue
            value = normalized[key]
            error_key = f'{prefix}{key}'
            if value is None:
                raise serializers.ValidationError({field_name: f'{error_key} cannot be empty.'})
            if spec.get('type') == 'number':
                if isinstance(value, bool):
                    raise serializers.ValidationError({field_name: f'{error_key} must be a number.'})
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    raise serializers.ValidationError({field_name: f'{error_key} must be a number.'})
                if not (-float('inf') < number < float('inf')):
                    raise serializers.ValidationError({field_name: f'{error_key} must be finite.'})
                if float(spec.get('step', 1)).is_integer() and not number.is_integer():
                    raise serializers.ValidationError({field_name: f'{error_key} must be an integer.'})
                if spec.get('min') is not None and number < spec['min']:
                    raise serializers.ValidationError({field_name: f'{error_key} must be at least {spec["min"]}.'})
                if spec.get('max') is not None and number > spec['max']:
                    raise serializers.ValidationError({field_name: f'{error_key} must be at most {spec["max"]}.'})
                normalized[key] = int(number) if float(spec.get('step', 1)).is_integer() and number.is_integer() else number
            elif spec.get('type') == 'select':
                choices = {choice['value'] for choice in spec.get('options', [])}
                if value not in choices:
                    raise serializers.ValidationError({field_name: f'{error_key} is not a supported choice.'})
                normalized[key] = value
            elif spec.get('type') == 'enum':
                choices = {choice[0] for choice in CandlePatternType.choices}
                if value not in choices:
                    raise serializers.ValidationError({field_name: f'{error_key} is not a supported candle pattern.'})
            elif spec.get('type') == 'source':
                allowed_sources = {choice['value'] for choice in spec.get('options', [])}
                if value not in allowed_sources:
                    raise serializers.ValidationError({field_name: f'{error_key} is not a supported price or indicator source.'})
                try:
                    source_type = OperandType(str(value).upper())
                except ValueError:
                    source_type = None
                if source_type in OPERAND_PARAMETER_CONFIG:
                    source_schema = OPERAND_PARAMETER_CONFIG[source_type]
                    raw_source_params = normalized.get('source_params') or {}
                    if not isinstance(raw_source_params, dict):
                        raise serializers.ValidationError({field_name: 'source_params must be an object.'})
                    source_params = raw_source_params
                    source_defaults = get_operand_parameter_defaults(source_type)
                    # Source indicators are configured inside source_params; their own source/shift controls are not nested.
                    source_defaults.pop('source', None)
                    source_defaults.pop('shift', None)
                    source_params = {**source_defaults, **source_params}
                    nested_schema = [item for item in source_schema if item['key'] not in {'source'}]
                    normalized['source_params'] = validate_fields(source_params, nested_schema, 'source_params.')
        return normalized

    params = validate_fields(params, schema)

    if operand_type == OperandType.MACD and params['fast_period'] >= params['slow_period']:
        raise serializers.ValidationError({field_name: 'fast_period must be less than slow_period.'})

    if operand_type == OperandType.MATH_EXPRESSION:
        expression_config = params.get('expression') or {}
        if isinstance(expression_config, str):
            expression_config = {'expression': expression_config, 'variables': params.get('variables') or {}}
        if not isinstance(expression_config, dict):
            raise serializers.ValidationError({field_name: 'Math expression must be an object.'})
        expression = str(expression_config.get('expression') or '')
        variables = expression_config.get('variables') or {}
        if not isinstance(variables, dict):
            raise serializers.ValidationError({field_name: 'Math expression variables must be an object.'})
        if not is_safe_arithmetic_expression(expression, variables.keys()):
            raise serializers.ValidationError({field_name: 'Enter a valid arithmetic expression using configured variables and numeric constants.'})
        normalized_variables = {}
        for name, config in variables.items():
            if not isinstance(name, str) or not name.startswith('VAR_') or not name[4:].isdigit():
                raise serializers.ValidationError({field_name: f'Invalid math variable name: {name}.'})
            if not isinstance(config, dict):
                raise serializers.ValidationError({field_name: f'{name} configuration must be an object.'})
            try:
                variable_type = OperandType(config.get('type'))
            except (TypeError, ValueError):
                raise serializers.ValidationError({field_name: f'{name} has an unsupported operand type.'})
            
            if variable_type.value not in (math_variable_types or ()):
                raise serializers.ValidationError({field_name: f'{variable_type.label} cannot be used as a numeric math variable.'})
            variable_params = _normalize_and_validate_operand_params(
                variable_type, config.get('params') or {}, field_name,
                math_variable_types=math_variable_types,
            )
            
            variable_timeframe = config.get('timeframe')
            if variable_timeframe and variable_timeframe not in {choice[0] for choice in CandleTimeframe.choices}:
                raise serializers.ValidationError({field_name: f'{name} has an unsupported timeframe.'})
            
            normalized_variables[name] = {**config, 'type': variable_type.value, 'params': variable_params, 'timeframe': variable_timeframe}
        expression_config = {**expression_config, 'expression': expression, 'variables': normalized_variables}
        params['expression'] = expression_config

    return params


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
        def value(field, default=None):
            if field in attrs:
                return attrs[field]
            if self.instance is not None:
                return getattr(self.instance, field)
            return default

        op_a_type = value('operand_a_type')
        op_b_type = value('operand_b_type')
        comparison = value('comparison')
        rule_group = value('rule_group')
        rule_type = getattr(rule_group, 'rule_type', None)
        math_variable_types = set(get_math_expression_operand_types(rule_type))

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

        for field, type_field, operand_type in (
            ('operand_a_params', 'operand_a_type', op_a_type),
            ('operand_b_params', 'operand_b_type', op_b_type),
        ):
            if not operand_type:
                continue

            type_changed = self.instance is not None and type_field in attrs and attrs[type_field] != getattr(self.instance, type_field)
            should_normalize = self.instance is None or field in attrs or type_changed
            
            if not should_normalize:
                continue

            raw_params = attrs.get(field) or {}
            attrs[field] = _normalize_and_validate_operand_params(
                operand_type, raw_params, field,
                math_variable_types=math_variable_types,
            )

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
