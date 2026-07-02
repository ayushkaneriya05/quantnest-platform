"""
Serializers for the strategies app.
"""
from rest_framework import serializers
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig, ReEntryRule
from common.enums import LogicalOperator


# ... (StrategyTagSerializer, EntryOrderConfigSerializer, ReEntryRuleSerializer, StrategyVersionSerializer, StrategyListSerializer remain unchanged)


class StrategyTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyTag
        fields = ['id', 'name', 'description']


class EntryOrderConfigSerializer(serializers.ModelSerializer):
    entry_group_operator = serializers.ChoiceField(choices=LogicalOperator.choices, required=False)
    
    class Meta:
        model = EntryOrderConfig
        fields = [
            'id', 'strategy', 'entry_side', 'entry_group_operator', 'order_type', 'entry_price_logic', 'price_offset',
            'allow_partial_entry', 'entry_cooldown_seconds'
        ]

    def validate(self, attrs):
        cooldown = attrs.get('entry_cooldown_seconds', getattr(self.instance, 'entry_cooldown_seconds', None))

        if cooldown is not None and cooldown < 0:
            raise serializers.ValidationError({'entry_cooldown_seconds': 'Entry cooldown cannot be negative.'})
        return attrs


class ExitOrderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitOrderConfig
        fields = ['id', 'stop_loss_group_operator', 'target_group_operator']


class ReEntryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReEntryRule
        fields = [
            'id', 'allow_reentry', 'max_reentries', 'reentry_cooldown_seconds',
            'allow_reverse_entry', 
            'loss_recovery_mode', 'loss_recovery_multiplier'
        ]

    def validate(self, attrs):
        allow_reentry = attrs.get('allow_reentry', getattr(self.instance, 'allow_reentry', True))
        max_reentries = attrs.get('max_reentries', getattr(self.instance, 'max_reentries', None))
        cooldown = attrs.get('reentry_cooldown_seconds', getattr(self.instance, 'reentry_cooldown_seconds', None))
        loss_recovery = attrs.get('loss_recovery_mode', getattr(self.instance, 'loss_recovery_mode', False))
        multiplier = attrs.get('loss_recovery_multiplier', getattr(self.instance, 'loss_recovery_multiplier', None))

        if allow_reentry and (max_reentries is None or max_reentries < 0 or max_reentries > 20):
            raise serializers.ValidationError({'max_reentries': 'Max re-entries must be between 0 and 20.'})
        if cooldown is not None and cooldown < 0:
            raise serializers.ValidationError({'reentry_cooldown_seconds': 'Re-entry cooldown cannot be negative.'})
        if loss_recovery and (multiplier is None or multiplier < 1 or multiplier > 3):
            raise serializers.ValidationError({'loss_recovery_multiplier': 'Loss-recovery multiplier must be between 1 and 3.'})
        return attrs


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
    entry_order_config = EntryOrderConfigSerializer(read_only=True)
    exit_order_config = ExitOrderConfigSerializer(read_only=True)
    reentry_rule = ReEntryRuleSerializer(read_only=True)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'status', 'visibility',
            'paper_trading_enabled', 'live_trading_enabled',
            'allow_clone', 'allow_backtest',
            'user', 'user_username', 'tags', 'tag_ids',
            'entry_order_config', 'exit_order_config', 'reentry_rule',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 
                           'created_at', 'updated_at']

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        validated_data['user'] = self.context['request'].user
        strategy = Strategy.objects.create(**validated_data)
        strategy.tags.set(tags)
        return strategy


class StrategyVersionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = StrategyVersion
        fields = ['id', 'version_number', 'config_snapshot', 'change_notes', 
                  'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['created_at']


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
            'allow_clone', 'allow_backtest',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]


class StrategyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new strategy."""
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'visibility', 'status',
            'auto_version_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['status'] = 'DRAFT'
        strategy = Strategy.objects.create(**validated_data)
        return strategy



