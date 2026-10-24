"""
Serializers for the rules_engine app.
"""
from rest_framework import serializers
from .models import PositionSizingRule, TimeRule, RuleGroup, Rule
from .math_expressions import parse_arithmetic_expression
from common.enums import QuantityType, OperandType, POSITION_OPERANDS, ComparisonOperator, CandlePatternType, CandleTimeframe, TradingDay, get_math_expression_operand_types, get_operand_parameter_config, get_operand_parameter_defaults, OPERAND_PARAMETER_CONFIG


def _normalize_and_validate_operand_params(operand_type, raw_params, field_name, math_variable_types=None):
    """Fill server-owned operand defaults and validate against the UI schema."""
    try:
        operand_type = OperandType(operand_type)
    except (TypeError, ValueError):
        return raw_params or {}

    if not isinstance(raw_params, dict):
        raise serializers.ValidationError({field_name: 'Parameters must be an object.'})
    if operand_type in POSITION_OPERANDS and raw_params.get('shift', 0):
        raise serializers.ValidationError({field_name: 'Position state has no historical candle shift.'})

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
                if not isinstance(value, str) or value.upper() not in allowed_sources:
                    raise serializers.ValidationError({field_name: f'{error_key} is not a supported price or indicator source.'})
                value = value.upper()
                normalized[key] = value
                try:
                    source_type = OperandType(value)
                except ValueError:
                    source_type = None
                if source_type in OPERAND_PARAMETER_CONFIG:
                    source_schema = OPERAND_PARAMETER_CONFIG[source_type]
                    raw_source_params = normalized.get('source_params') or {}
                    if not isinstance(raw_source_params, dict):
                        raise serializers.ValidationError({field_name: 'source_params must be an object.'})
                    allowed = {item['key'] for item in source_schema if item['key'] != 'source'}
                    if set(raw_source_params) - allowed:
                        raise serializers.ValidationError({field_name: 'A source indicator accepts its displayed parameters only; nested sources and source shifts are not supported.'})
                    source_params = raw_source_params
                    source_defaults = get_operand_parameter_defaults(source_type)
                    # Source indicators are configured inside source_params; their own source/shift controls are not nested.
                    source_defaults.pop('source', None)
                    source_defaults.pop('shift', None)
                    source_params = {**source_defaults, **source_params}
                    nested_schema = [item for item in source_schema if item['key'] not in {'source'}]
                    normalized['source_params'] = validate_fields(source_params, nested_schema, 'source_params.')
                    if source_type == OperandType.MACD and normalized['source_params']['fast_period'] >= normalized['source_params']['slow_period']:
                        raise serializers.ValidationError({field_name: 'Source fast_period must be less than slow_period.'})
        return normalized

    params = validate_fields(params, schema)

    if operand_type == OperandType.MACD and params['fast_period'] >= params['slow_period']:
        raise serializers.ValidationError({field_name: 'fast_period must be less than slow_period.'})

    if operand_type == OperandType.MATH_EXPRESSION:
        expression_config = params.get('expression') or {}
        if not isinstance(expression_config, dict):
            raise serializers.ValidationError({field_name: 'Math expression must be an object.'})
        expression = str(expression_config.get('expression') or '')
        variables = expression_config.get('variables') or {}
        if not isinstance(variables, dict):
            raise serializers.ValidationError({field_name: 'Math expression variables must be an object.'})
        try:
            parse_arithmetic_expression(expression, variables)
        except ValueError as exc:
            raise serializers.ValidationError({field_name: str(exc)}) from None
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


class StrategyConfigSerializer(serializers.ModelSerializer):
    """Writable strategy relations must belong to the caller and remain fixed."""
    def validate_strategy(self, strategy):
        request = self.context.get('request')
        if request and strategy.user_id != request.user.pk:
            raise serializers.ValidationError('Select one of your own strategies.')
        if self.instance and strategy.pk != self.instance.strategy_id:
            raise serializers.ValidationError('A configuration cannot be moved to another strategy.')
        return strategy


class TimeRuleSerializer(StrategyConfigSerializer):
    def validate(self, attrs):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        zone = attrs.get('timezone', getattr(self.instance, 'timezone', 'Asia/Kolkata'))
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise serializers.ValidationError({'timezone': 'Choose a valid IANA timezone.'}) from None
        days = attrs.get('trading_days', getattr(self.instance, 'trading_days', []))
        if not isinstance(days, list) or any(not isinstance(day, str) or day.title() not in TradingDay.values for day in days):
            raise serializers.ValidationError({'trading_days': 'Provide a list of weekday names.'})
        if 'trading_days' in attrs:
            attrs['trading_days'] = [day.title() for day in days]
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and start >= end:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        from datetime import time
        windows = attrs.get('no_trade_windows', getattr(self.instance, 'no_trade_windows', [])) or []
        try:
            if not isinstance(windows, list):
                raise ValueError()
            for window in windows:
                if not isinstance(window, dict) or time.fromisoformat(window['start']) >= time.fromisoformat(window['end']):
                    raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise serializers.ValidationError({'no_trade_windows': 'Each window needs valid start/end times in order.'}) from None
        return attrs

    class Meta:
        model = TimeRule
        fields = [
            'id', 'strategy', 'trading_days', 'market_session',
            'start_time', 'end_time', 'candle_timeframe',
            'no_trade_windows', 'timezone'
        ]


class RuleSerializer(serializers.ModelSerializer):
    def validate_rule_group(self, group):
        request = self.context.get('request')
        if request and group.strategy.user_id != request.user.pk:
            raise serializers.ValidationError('Select a rule group from your own strategy.')
        if self.instance and group.pk != self.instance.rule_group_id:
            raise serializers.ValidationError('A rule cannot be moved to another group.')
        return group

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
        rule_type = getattr(rule_group, 'rule_type', self.context.get('rule_type'))
        math_variable_types = set(get_math_expression_operand_types(rule_type))
        if rule_type == 'ENTRY' and any(operand in POSITION_OPERANDS for operand in (op_a_type, op_b_type)):
            raise serializers.ValidationError('Position operands are available only in exit rules.')

        if not op_a_type:
            raise serializers.ValidationError({"operand_a_type": "Operand A type is required."})
        if not op_b_type or not comparison:
            raise serializers.ValidationError('Each rule requires two operands and a comparison.')

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


class RuleGroupSerializer(StrategyConfigSerializer):
    rules = RuleSerializer(many=True, read_only=True)

    class Meta:
        model = RuleGroup
        fields = [
            'id', 'strategy', 'name', 'rule_type', 'logical_operator',
            'priority',
            'is_active', 'rules'
        ]


class PositionSizingRuleSerializer(StrategyConfigSerializer):
    class Meta:
        model = PositionSizingRule
        fields = [
            'id', 'strategy', 'sizing_method', 'fixed_quantity', 'capital_percentage',
        ]

    def validate(self, attrs):
        method = attrs.get('sizing_method', getattr(self.instance, 'sizing_method', QuantityType.CAPITAL_BASED))
        fixed_quantity = attrs.get('fixed_quantity', getattr(self.instance, 'fixed_quantity', None))
        capital_percentage = attrs.get('capital_percentage', getattr(self.instance, 'capital_percentage', None))

        if method == QuantityType.FIXED and (fixed_quantity is None or fixed_quantity < 1):
            raise serializers.ValidationError({'fixed_quantity': 'Fixed quantity must be at least 1.'})
        if method == QuantityType.CAPITAL_BASED and (capital_percentage is None or capital_percentage <= 0 or capital_percentage > 100):
            raise serializers.ValidationError({'capital_percentage': 'Capital percentage must be between 0 and 100.'})

        return attrs
