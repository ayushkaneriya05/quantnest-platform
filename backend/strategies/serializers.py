"""
Serializers for the strategies app.
"""
from rest_framework import serializers
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig
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
            'id', 'strategy', 'entry_side', 'entry_group_operator', 'order_type', 'price_offset',
            'cooldown_seconds'
        ]

    def validate(self, attrs):
        cooldown = attrs.get('cooldown_seconds', getattr(self.instance, 'cooldown_seconds', None))

        if cooldown is not None and cooldown < 0:
            raise serializers.ValidationError({'cooldown_seconds': 'Cooldown cannot be negative.'})
        return attrs


class ExitOrderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitOrderConfig
        fields = ['id', 'exit_group_operator', 'stop_loss_group_operator', 'target_group_operator']


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
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'description', 'strategy_type', 'market_type',
            'exchange', 'instrument_type', 'status', 'visibility',
            'paper_trading_enabled', 'live_trading_enabled',
            'allow_clone', 'allow_backtest',
            'user', 'user_username', 'tags', 'tag_ids',
            'entry_order_config', 'exit_order_config',
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


class StrategyVersionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for version dropdowns."""
    class Meta:
        model = StrategyVersion
        fields = ['id', 'version_number', 'change_notes', 'created_at']
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
