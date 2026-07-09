"""
Serializers for the rules_engine app.
"""
from rest_framework import serializers
from common.enums import RuleCategory, StopLossType, TargetType
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule, StopLossRule, TargetRule


RULE_CLASSIFICATION_FIELDS = {
    'indicator_type',
    'price_action_type',
    'volume_condition_type',
    'compare_to_indicator',
    'compare_to_params',
}

STOP_LOSS_TYPE_FIELDS = {
    'fixed_points',
    'fixed_percentage',
    'indicator_type',
    'indicator_params',
    'operator',
    'threshold_value',
    'threshold_value2',
    'compare_to_indicator',
    'compare_to_params',
    'timeframe_override',
    'candle_part',
    'candle_offset',
    'candle_lookback',
    'trailing_value',
    'time_minutes',
    'emergency_loss_pct',
}

TARGET_TYPE_FIELDS = {
    'fixed_points',
    'fixed_percentage',
    'risk_reward_ratio',
    'indicator_type',
    'indicator_params',
    'operator',
    'threshold_value',
    'threshold_value2',
    'compare_to_indicator',
    'compare_to_params',
    'timeframe_override',
    'trailing_value',
    'time_exit_minutes',
    'eod_squareoff_time',
    'expiry_exit_minutes_before',
}


def _positive(attrs, field, label=None, *, allow_zero=False, instance=None):
    value = attrs.get(field, getattr(instance, field, None))
    if value is None:
        raise serializers.ValidationError({field: f"{label or field} is required."})
    if allow_zero:
        valid = value >= 0
    else:
        valid = value > 0
    if not valid:
        raise serializers.ValidationError({field: f"{label or field} must be greater than {'or equal to ' if allow_zero else ''}zero."})
    return value


def _clear_fields(attrs, fields, keep=(), defaults=None):
    defaults = defaults or {}
    keep = set(keep or ())
    for field in fields:
        if field in keep:
            continue
        attrs[field] = defaults.get(field)


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
            'id', 'rule_group', 'category', 'indicator_type', 'price_action_type',
            'volume_condition_type', 'params', 'comparison', 'value', 'value2',
            'compare_to_indicator', 'compare_to_params', 'timeframe_override',
            'is_active'
        ]

    def validate(self, attrs):
        category = attrs.get('category', getattr(self.instance, 'category', None))
        indicator_type = attrs.get('indicator_type', getattr(self.instance, 'indicator_type', None))
        price_action_type = attrs.get('price_action_type', getattr(self.instance, 'price_action_type', None))
        volume_condition_type = attrs.get('volume_condition_type', getattr(self.instance, 'volume_condition_type', None))
        params = attrs.get('params', getattr(self.instance, 'params', None)) or {}

        if category == RuleCategory.INDICATOR:
            _clear_fields(attrs, RULE_CLASSIFICATION_FIELDS, keep=('indicator_type', 'compare_to_indicator', 'compare_to_params'))
        elif category == RuleCategory.PRICE_ACTION:
            _clear_fields(attrs, RULE_CLASSIFICATION_FIELDS, keep=('price_action_type',))
            attrs['value'] = None
            attrs['value2'] = None
        elif category == RuleCategory.VOLUME:
            _clear_fields(attrs, RULE_CLASSIFICATION_FIELDS, keep=('volume_condition_type',))
            attrs['value'] = None
            attrs['value2'] = None
        elif category == RuleCategory.CUSTOM:
            _clear_fields(attrs, RULE_CLASSIFICATION_FIELDS)
            attrs['value'] = None
            attrs['value2'] = None

        indicator_type = attrs.get('indicator_type', getattr(self.instance, 'indicator_type', None))
        price_action_type = attrs.get('price_action_type', getattr(self.instance, 'price_action_type', None))
        volume_condition_type = attrs.get('volume_condition_type', getattr(self.instance, 'volume_condition_type', None))
        params = attrs.get('params', getattr(self.instance, 'params', None)) or {}

        if category == RuleCategory.INDICATOR and not indicator_type:
            raise serializers.ValidationError({'indicator_type': 'Indicator rules require an indicator type.'})
        if category == RuleCategory.PRICE_ACTION and not price_action_type:
            raise serializers.ValidationError({'price_action_type': 'Price-action rules require a price-action type.'})
        if category == RuleCategory.VOLUME and not volume_condition_type:
            raise serializers.ValidationError({'volume_condition_type': 'Volume rules require a volume condition type.'})
        if category == RuleCategory.CUSTOM and not params.get('expression'):
            raise serializers.ValidationError({'params': 'Custom rules require an expression over open/high/low/close/volume.'})

        for key in ('period', 'length', 'lookback', 'fast_period', 'slow_period', 'signal_period', 'k_period', 'd_period', 'smooth'):
            if key in params and params[key] is not None and int(params[key]) < 1:
                raise serializers.ValidationError({'params': f'{key} must be at least 1.'})
        return attrs





class RuleGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleGroup
        fields = [
            'id', 'strategy', 'name', 'rule_type', 'logical_operator',
            'priority'
        ]
        read_only_fields = ['id']


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

    def validate(self, attrs):
        sl_type = attrs.get('sl_type', getattr(self.instance, 'sl_type', None))
        keep = set()
        defaults = {'candle_offset': 0, 'candle_lookback': 1}

        if sl_type == StopLossType.FIXED_POINTS:
            keep = {'fixed_points'}
        elif sl_type == StopLossType.FIXED_PERCENTAGE:
            keep = {'fixed_percentage'}
        elif sl_type in {StopLossType.TRAILING_FIXED, StopLossType.TRAILING_PERCENTAGE}:
            keep = {'trailing_value'}
        elif sl_type == StopLossType.INDICATOR_BASED:
            keep = {'indicator_type', 'indicator_params', 'operator', 'threshold_value', 'threshold_value2', 'compare_to_indicator', 'compare_to_params', 'timeframe_override'}
        elif sl_type == StopLossType.TRAILING_INDICATOR:
            keep = {'indicator_type', 'indicator_params', 'timeframe_override'}
        elif sl_type == StopLossType.TIME_BASED:
            keep = {'time_minutes'}
        elif sl_type == StopLossType.EMERGENCY:
            keep = {'emergency_loss_pct'}
        elif sl_type == StopLossType.CANDLE_BASED:
            keep = {'candle_part', 'candle_offset', 'candle_lookback'}

        _clear_fields(attrs, STOP_LOSS_TYPE_FIELDS, keep=keep, defaults=defaults)

        if sl_type == StopLossType.FIXED_POINTS:
            _positive(attrs, 'fixed_points', 'Fixed points', instance=self.instance)
        elif sl_type == StopLossType.FIXED_PERCENTAGE:
            _positive(attrs, 'fixed_percentage', 'Fixed percentage', instance=self.instance)
        elif sl_type in {StopLossType.TRAILING_FIXED, StopLossType.TRAILING_PERCENTAGE}:
            _positive(attrs, 'trailing_value', 'Trailing value', instance=self.instance)
        elif sl_type == StopLossType.INDICATOR_BASED:
            if not attrs.get('indicator_type', getattr(self.instance, 'indicator_type', None)):
                raise serializers.ValidationError({'indicator_type': 'Indicator-based stop loss requires an indicator.'})
            if (
                attrs.get('threshold_value', getattr(self.instance, 'threshold_value', None)) is None
                and not attrs.get('compare_to_indicator', getattr(self.instance, 'compare_to_indicator', None))
            ):
                raise serializers.ValidationError({'threshold_value': 'Indicator-based stop loss requires a threshold or comparison indicator.'})
        elif sl_type == StopLossType.TRAILING_INDICATOR:
            if not attrs.get('indicator_type', getattr(self.instance, 'indicator_type', None)):
                raise serializers.ValidationError({'indicator_type': 'Trailing indicator stop loss requires an indicator.'})
        elif sl_type == StopLossType.TIME_BASED:
            _positive(attrs, 'time_minutes', 'Time minutes', instance=self.instance)
        elif sl_type == StopLossType.EMERGENCY:
            _positive(attrs, 'emergency_loss_pct', 'Emergency loss percentage', instance=self.instance)
        elif sl_type == StopLossType.CANDLE_BASED:
            _positive(attrs, 'candle_lookback', 'Candle lookback', instance=self.instance)
        return attrs


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

    def validate(self, attrs):
        target_type = attrs.get('target_type', getattr(self.instance, 'target_type', None))
        keep = set()

        if target_type == TargetType.FIXED_POINTS:
            keep = {'fixed_points'}
        elif target_type == TargetType.FIXED_PERCENTAGE:
            keep = {'fixed_percentage'}
        elif target_type == TargetType.RISK_REWARD:
            keep = {'risk_reward_ratio'}
        elif target_type == TargetType.INDICATOR_BASED:
            keep = {'indicator_type', 'indicator_params', 'operator', 'threshold_value', 'threshold_value2', 'compare_to_indicator', 'compare_to_params', 'timeframe_override'}
        elif target_type in {TargetType.TRAILING_FIXED, TargetType.TRAILING_PERCENTAGE}:
            keep = {'trailing_value'}
        elif target_type == TargetType.TIME_BASED:
            keep = {'time_exit_minutes'}
        elif target_type == TargetType.EOD:
            keep = {'eod_squareoff_time'}
        elif target_type == TargetType.EXPIRY:
            keep = {'expiry_exit_minutes_before'}

        _clear_fields(attrs, TARGET_TYPE_FIELDS, keep=keep)

        if target_type == TargetType.FIXED_POINTS:
            _positive(attrs, 'fixed_points', 'Fixed points', instance=self.instance)
        elif target_type == TargetType.FIXED_PERCENTAGE:
            _positive(attrs, 'fixed_percentage', 'Fixed percentage', instance=self.instance)
        elif target_type == TargetType.RISK_REWARD:
            _positive(attrs, 'risk_reward_ratio', 'Risk-reward ratio', instance=self.instance)
        elif target_type == TargetType.INDICATOR_BASED:
            if not attrs.get('indicator_type', getattr(self.instance, 'indicator_type', None)):
                raise serializers.ValidationError({'indicator_type': 'Indicator-based target requires an indicator.'})
            if (
                attrs.get('threshold_value', getattr(self.instance, 'threshold_value', None)) is None
                and not attrs.get('compare_to_indicator', getattr(self.instance, 'compare_to_indicator', None))
            ):
                raise serializers.ValidationError({'threshold_value': 'Indicator-based target requires a threshold or comparison indicator.'})
        elif target_type in {TargetType.TRAILING_FIXED, TargetType.TRAILING_PERCENTAGE}:
            _positive(attrs, 'trailing_value', 'Trailing value', instance=self.instance)
        elif target_type == TargetType.TIME_BASED:
            _positive(attrs, 'time_exit_minutes', 'Time exit minutes', instance=self.instance)
        elif target_type == TargetType.EOD:
            if not attrs.get('eod_squareoff_time', getattr(self.instance, 'eod_squareoff_time', None)):
                raise serializers.ValidationError({'eod_squareoff_time': 'EOD target requires a square-off time.'})
        elif target_type == TargetType.EXPIRY:
            _positive(attrs, 'expiry_exit_minutes_before', 'Expiry exit minutes', instance=self.instance)
        return attrs


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
