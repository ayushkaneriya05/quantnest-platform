"""Shared operand validation for strategy documents and research screens.

This is the authoring boundary. Execution compiles the accepted parameters once
and never runs serializer validation for each market event.
"""
from rest_framework import serializers

from common.enums import CandlePatternType, CandleTimeframe, OperandType
from strategies.specification.operands import POSITION_OPERANDS, PARAMETERS, get_operand_parameter_config, get_operand_parameter_defaults
from execution.expressions import parse_arithmetic_expression
from .specification.expressions import ARITHMETIC_VARIABLE_PREFIX


def validate_operand_parameters(operand_type: OperandType, raw_params: dict, field_name: str,
                                *, math_variable_types: set[str]) -> dict:
    """Fill server-owned operand defaults and validate against the UI schema."""
    if not isinstance(raw_params, dict):
        raise serializers.ValidationError({field_name: 'Parameters must be an object.'})
    if operand_type in POSITION_OPERANDS and raw_params.get('shift', 0):
        raise serializers.ValidationError({field_name: 'Position state has no historical candle shift.'})
    if operand_type == OperandType.LTP and raw_params.get('shift', 0):
        raise serializers.ValidationError({field_name: 'A live price has no historical candle shift.'})

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
                if source_type in PARAMETERS:
                    source_schema = PARAMETERS[source_type]
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
            if (not isinstance(name, str) or not name.startswith(ARITHMETIC_VARIABLE_PREFIX)
                    or not name[len(ARITHMETIC_VARIABLE_PREFIX):].isdigit()):
                raise serializers.ValidationError({field_name: f'Invalid math variable name: {name}.'})
            if not isinstance(config, dict):
                raise serializers.ValidationError({field_name: f'{name} configuration must be an object.'})
            try:
                variable_type = OperandType(config.get('type'))
            except (TypeError, ValueError):
                raise serializers.ValidationError({field_name: f'{name} has an unsupported operand type.'})
            
            if variable_type.value not in math_variable_types:
                raise serializers.ValidationError({field_name: f'{variable_type.label} cannot be used as a numeric math variable.'})
            variable_params = validate_operand_parameters(
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
