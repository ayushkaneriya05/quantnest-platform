"""
Serializers for the strategies app.
"""
from datetime import time
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from rest_framework import serializers

from common.enums import (
    CandleTimeframe,
    LogicalOperator, MarketSession, QuantityType, QuantityUnit,
    Side, Timezone, TradingDay,
)
from .specification.configuration import (SCHEDULE_FIELDS, SIZING_FIELDS, ENTRY_FIELDS, EXIT_FIELDS, default_trading_days)
from .models import Strategy, StrategyVersion, StrategyTag


class StrategyTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyTag
        fields = ['id', 'name', 'description']


class TimeRuleSerializer(serializers.Serializer):
    """Entry schedule; accepted exit rules remain active outside this window."""
    trading_days = serializers.ListField(child=serializers.CharField(), default=default_trading_days)
    market_session = serializers.ChoiceField(choices=MarketSession.choices, default=SCHEDULE_FIELDS['market_session']['default'])
    start_time = serializers.TimeField(allow_null=True, default=time.fromisoformat(SCHEDULE_FIELDS['start_time']['default']))
    end_time = serializers.TimeField(allow_null=True, default=time.fromisoformat(SCHEDULE_FIELDS['end_time']['default']))
    candle_timeframe = serializers.ChoiceField(choices=CandleTimeframe.choices, default=SCHEDULE_FIELDS['candle_timeframe']['default'])
    no_trade_windows = serializers.JSONField(allow_null=True, default=list)
    timezone = serializers.ChoiceField(choices=Timezone.choices, default=SCHEDULE_FIELDS['timezone']['default'])

    def validate(self, attrs):
        zone = attrs['timezone']
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise serializers.ValidationError({'timezone': 'Choose a valid IANA timezone.'}) from None
        days = attrs['trading_days']
        if any(day.title() not in TradingDay.values for day in days):
            raise serializers.ValidationError({'trading_days': 'Provide a list of weekday names.'})
        attrs['trading_days'] = [day.title() for day in days]
        start = attrs['start_time']
        end = attrs['end_time']
        if start and end and start >= end:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        windows = attrs['no_trade_windows'] or []
        try:
            if not isinstance(windows, list):
                raise ValueError()
            for window in windows:
                if not isinstance(window, dict) or time.fromisoformat(window['start']) >= time.fromisoformat(window['end']):
                    raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise serializers.ValidationError({'no_trade_windows': 'Each window needs valid start/end times in order.'}) from None
        return attrs


class PositionSizingRuleSerializer(serializers.Serializer):
    """Default sizing and its units, shared by strategy details and documents."""
    sizing_method = serializers.ChoiceField(choices=QuantityType.choices, default=SIZING_FIELDS['sizing_method']['default'])
    fixed_quantity = serializers.IntegerField(min_value=SIZING_FIELDS['fixed_quantity']['min'], allow_null=True, default=SIZING_FIELDS['fixed_quantity']['default'])
    capital_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True, default=Decimal(SIZING_FIELDS['capital_percentage']['default']))
    quantity_unit = serializers.ChoiceField(choices=QuantityUnit.choices, default=SIZING_FIELDS['quantity_unit']['default'])

    def validate(self, attrs):
        method = attrs['sizing_method']
        fixed_quantity = attrs['fixed_quantity']
        capital_percentage = attrs['capital_percentage']

        if method == QuantityType.FIXED and (fixed_quantity is None or fixed_quantity < 1):
            raise serializers.ValidationError({'fixed_quantity': 'Fixed quantity must be at least 1.'})
        if method == QuantityType.CAPITAL_BASED and (capital_percentage is None or capital_percentage < SIZING_FIELDS['capital_percentage']['min'] or capital_percentage > SIZING_FIELDS['capital_percentage']['max']):
            raise serializers.ValidationError({'capital_percentage': 'Capital percentage must be between 0 and 100.'})

        return attrs


class SizingOverrideSerializer(serializers.Serializer):
    """Optional per-instrument sizing; execution has no route-type selector."""
    override_sizing = serializers.BooleanField(default=False)
    sizing_method = serializers.ChoiceField(choices=QuantityType.choices, allow_null=True, default=None)
    quantity_unit = serializers.ChoiceField(choices=QuantityUnit.choices, default=SIZING_FIELDS['quantity_unit']['default'])
    fixed_quantity = serializers.IntegerField(min_value=SIZING_FIELDS['fixed_quantity']['min'], allow_null=True, default=None)
    capital_percentage = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True, default=None)

    def validate(self, attrs):
        override = attrs.get("override_sizing", False)
        method = attrs.get("sizing_method")
        quantity = attrs.get("fixed_quantity")
        percentage = attrs.get("capital_percentage")
        if override:
            if method not in QuantityType.values:
                raise serializers.ValidationError({"sizing_method": "Choose fixed quantity or capital-based sizing."})
            if method == QuantityType.FIXED and (quantity is None or quantity < 1):
                raise serializers.ValidationError({"fixed_quantity": "Quantity must be at least 1."})
            if method == QuantityType.CAPITAL_BASED and (percentage is None or not SIZING_FIELDS['capital_percentage']['min'] <= percentage <= SIZING_FIELDS['capital_percentage']['max']):
                raise serializers.ValidationError({"capital_percentage": "Capital percentage must be greater than 0 and at most 100."})
        return attrs


class EntryOrderConfigSerializer(serializers.Serializer):
    entry_side = serializers.ChoiceField(choices=Side.choices, default=ENTRY_FIELDS['entry_side']['default'])
    entry_group_operator = serializers.ChoiceField(choices=LogicalOperator.choices, default=ENTRY_FIELDS['entry_group_operator']['default'])
    order_type = serializers.ChoiceField(choices=ENTRY_FIELDS['order_type']['values'], default=ENTRY_FIELDS['order_type']['default'])


class ExitOrderConfigSerializer(serializers.Serializer):
    exit_group_operator = serializers.ChoiceField(choices=LogicalOperator.choices, default=EXIT_FIELDS['exit_group_operator']['default'])
    stop_loss_group_operator = serializers.ChoiceField(choices=LogicalOperator.choices, default=EXIT_FIELDS['stop_loss_group_operator']['default'])
    target_group_operator = serializers.ChoiceField(choices=LogicalOperator.choices, default=EXIT_FIELDS['target_group_operator']['default'])


class StrategyDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested configs."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    tags = StrategyTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=StrategyTag.objects.all(),
        many=True,
        write_only=True,
        source='tags',
        required=False
    )
    entry_order_config = EntryOrderConfigSerializer(source='definition.entry_order_config', read_only=True)
    exit_order_config = ExitOrderConfigSerializer(source='definition.exit_order_config', read_only=True)
    position_sizing_rule = PositionSizingRuleSerializer(source='definition.position_sizing_rule', read_only=True)

    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'status', 'visibility',
            'paper_trading_enabled', 'live_trading_enabled',
            'user', 'user_username', 'tags', 'tag_ids',
            'entry_order_config', 'exit_order_config', 'position_sizing_rule',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance:
            for flag, session_relation in (
                ('paper_trading_enabled', 'paper_sessions'),
                ('live_trading_enabled', 'live_sessions'),
            ):
                if attrs.get(flag, getattr(self.instance, flag)):
                    continue
                if getattr(self.instance, session_relation).filter(status__in=['RUNNING', 'PAUSED']).exists():
                    raise serializers.ValidationError({flag: 'Stop all running or paused sessions before disabling this trading mode.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        validated_data['user'] = self.context['request'].user
        from commercial.usage import require_inventory_capacity
        require_inventory_capacity(validated_data['user'], strategies=1)
        strategy = Strategy.objects.create(**validated_data)
        strategy.tags.set(tags)
        return strategy


class StrategyVersionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    changes = serializers.SerializerMethodField()
    previous_version_number = serializers.SerializerMethodField()

    def previous_version(self, instance):
        if 'previous_versions' in self.context:
            return self.context['previous_versions'].get(instance.pk)
        if not hasattr(instance, '_previous_version'):
            instance._previous_version = instance.strategy.versions.filter(version_number__lt=instance.version_number).order_by('-version_number').first()
        return instance._previous_version

    def get_changes(self, instance):
        from .snapshots import snapshot_changes
        previous = self.previous_version(instance)
        return snapshot_changes(previous.config_snapshot if previous else None, instance.config_snapshot)

    def get_previous_version_number(self, instance):
        previous = self.previous_version(instance)
        return previous.version_number if previous else None

    class Meta:
        model = StrategyVersion
        fields = ['id', 'version_number', 'config_snapshot', 'change_notes', 
                  'created_by', 'created_by_username', 'created_at', 'changes', 'previous_version_number']
        read_only_fields = ['created_at']


class StrategyVersionListSerializer(serializers.ModelSerializer):
    """Snapshot metadata; the preview endpoint owns configuration and diffs."""
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    class Meta:
        model = StrategyVersion
        fields = ['id', 'version_number', 'change_notes', 'created_at', 'created_by_username']
        read_only_fields = fields


class StrategyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    tags = StrategyTagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'status', 'visibility',
            'user', 'user_username', 'tags',
            'paper_trading_enabled', 'live_trading_enabled',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]


class StrategyCreateSerializer(StrategyDetailSerializer):
    """Creation fields sharing the transactional save and inventory admission."""
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'visibility', 'status',
            'paper_trading_enabled', 'live_trading_enabled',
            'tag_ids',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['status'] = 'DRAFT'
        return super().create(validated_data)
