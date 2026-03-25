import logging
from django.db import transaction
from .models import Strategy, StrategyVersion, EntryOrderConfig, ExitOrderConfig, ReEntryRule
from .serializers import StrategyDetailSerializer
from rules_engine.models import RuleGroup, Rule, StopLossRule, TargetRule, TimeRule, SpecialEventFilter
from rules_engine.serializers import RuleGroupSerializer, TimeRuleSerializer, SpecialEventFilterSerializer

logger = logging.getLogger(__name__)

class StrategySnapshotService:
    """
    Service to handle strategy versioning: snapshotting and rolling back.
    """

    @staticmethod
    def create_snapshot(strategy, user=None, change_notes=None):
        """
        Creates a new version snapshot of the strategy.
        """
        try:
            # 1. Serialize the full strategy state
            # We use specific serializers or manual dict construction to ensure deep nesting is captured
            snapshot = StrategySnapshotService._serialize_strategy(strategy)
            
            # 2. Determine version number
            last_version = strategy.versions.order_by('-version_number').first()
            next_version = (last_version.version_number + 1) if last_version else 1
            
            # 3. Save Version
            version = StrategyVersion.objects.create(
                strategy=strategy,
                version_number=next_version,
                config_snapshot=snapshot,
                change_notes=change_notes,
                created_by=user
            )
            return version
        except Exception as e:
            logger.error(f"Error creating snapshot for strategy {strategy.id}: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def restore_version(strategy, version_id):
        """
        Restores the strategy to a specific version.
        WARNING: This is a destructive operation for the current configuration.
        """
        try:
            version = StrategyVersion.objects.get(id=version_id, strategy=strategy)
            snapshot = version.config_snapshot
            
            # 1. Restore Strategy Base Fields
            strategy.name = snapshot.get('name', strategy.name)
            strategy.description = snapshot.get('description', strategy.description)
            strategy.strategy_type = snapshot.get('strategy_type', strategy.strategy_type)
            strategy.market_type = snapshot.get('market_type', strategy.market_type)
            strategy.exchange = snapshot.get('exchange', strategy.exchange)
            strategy.instrument_type = snapshot.get('instrument_type', strategy.instrument_type)
            strategy.save()
            
            # 2. Restore 1:1 Configs (Update in place)
            if 'time_rule' in snapshot:
                StrategySnapshotService._restore_time_rule(strategy, snapshot['time_rule'])
                
            if 'special_event_filter' in snapshot:
                StrategySnapshotService._restore_event_filter(strategy, snapshot['special_event_filter'])
                
            if 'entry_order_config' in snapshot:
                StrategySnapshotService._restore_entry_config(strategy, snapshot['entry_order_config'])

            if 'reentry_rule' in snapshot:
                StrategySnapshotService._restore_reentry_rule(strategy, snapshot['reentry_rule'])
                
            if 'exit_order_config' in snapshot:
                StrategySnapshotService._restore_exit_config(strategy, snapshot['exit_order_config'])
                
            # 3. Restore Rule Groups (Delete all existing and recreate)
            # This is safer than trying to diff/update heavily nested structures
            strategy.rule_groups.all().delete()
            
            if 'rule_groups' in snapshot:
                for group_data in snapshot['rule_groups']:
                    StrategySnapshotService._restore_rule_group(strategy, group_data)
            
            # 4. Create a new version to represent this rollback state
            # This ensures the "Current" version in history matches the restored state
            StrategySnapshotService.create_snapshot(
                strategy, 
                change_notes=f"Rollback to version {version.version_number}"
            )

            return strategy
        except StrategyVersion.DoesNotExist:
            raise ValueError("Version not found")
        except Exception as e:
            logger.error(f"Error restoring version {version_id} for strategy {strategy.id}: {str(e)}")
            raise

    @staticmethod
    def _serialize_strategy(strategy):
        """
        Constructs a clean JSON dictionary of the strategy state.
        Uses DRF serializers where appropriate but ensures flattened structure for snapshot.
        """
        # We can re-use the detail serializer but might need more specific handling
        # Using the detail serializer is a good start as it includes most things
        from .serializers import StrategyDetailSerializer
        # We need to ensure deep nested fields like rules are included fully
        # The default DetailSerializer might be read_only or flattened differently
        
        # Let's build a custom robust dict
        data = {
            'name': strategy.name,
            'description': strategy.description,
            'strategy_type': strategy.strategy_type,
            'market_type': strategy.market_type,
            'exchange': strategy.exchange,
            'instrument_type': strategy.instrument_type,
        }
        
        # 1:1 Relations
        if hasattr(strategy, 'entry_order_config'):
            data['entry_order_config'] = StrategySnapshotService._model_to_dict(strategy.entry_order_config, exclude=['id', 'strategy', 'created_at', 'updated_at'])
            
        if hasattr(strategy, 'exit_order_config'):
             data['exit_order_config'] = StrategySnapshotService._model_to_dict(strategy.exit_order_config, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        if hasattr(strategy, 'reentry_rule'):
             data['reentry_rule'] = StrategySnapshotService._model_to_dict(strategy.reentry_rule, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        if hasattr(strategy, 'time_rule'):
             data['time_rule'] = StrategySnapshotService._model_to_dict(strategy.time_rule, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        if hasattr(strategy, 'special_event_filter'):
             data['special_event_filter'] = StrategySnapshotService._model_to_dict(strategy.special_event_filter, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        # Rule Groups (Deep nesting)
        groups = []
        for group in strategy.rule_groups.all().order_by('priority'):
            g_data = StrategySnapshotService._model_to_dict(group, exclude=['id', 'strategy', 'created_at', 'updated_at', 'rules', 'stop_loss_rules', 'target_rules'])
            
            # Rules
            g_data['rules'] = [StrategySnapshotService._model_to_dict(r, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for r in group.rules.all()]
            
            # Stop Losses
            g_data['stop_loss_rules'] = [StrategySnapshotService._model_to_dict(sl, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for sl in group.stop_loss_rules.all()]
            
            # Targets
            g_data['target_rules'] = [StrategySnapshotService._model_to_dict(t, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for t in group.target_rules.all()]
            
            groups.append(g_data)
        
        data['rule_groups'] = groups
        return data

    @staticmethod
    def _model_to_dict(instance, exclude=None):
        from django.forms.models import model_to_dict
        d = model_to_dict(instance, exclude=exclude)
        # Handle decimal/time/date serialization if needed (DRF JSONRenderer handles it usually, but raw model_to_dict might not for JSONField storage)
        # JSONField in model will handle basic types. Decimal might need casting to string or float.
        # For simplicity, we assume Django's JSONEncoder will handle it or we cast decimals.
        for key, value in d.items():
            import decimal
            import datetime
            if isinstance(value, decimal.Decimal):
                d[key] = float(value) # or str(value)
            elif isinstance(value, (datetime.time, datetime.date, datetime.datetime)):
                d[key] = value.isoformat()
        return d

    @staticmethod
    def _restore_time_rule(strategy, data):
        TimeRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_event_filter(strategy, data):
        SpecialEventFilter.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_entry_config(strategy, data):
        EntryOrderConfig.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_reentry_rule(strategy, data):
        ReEntryRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_exit_config(strategy, data):
        ExitOrderConfig.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_rule_group(strategy, group_data):
        rules_data = group_data.pop('rules', [])
        sl_data = group_data.pop('stop_loss_rules', [])
        target_data = group_data.pop('target_rules', [])
        
        # Create Group
        group = RuleGroup.objects.create(strategy=strategy, **group_data)
        
        # Create Nested Rules
        for r_data in rules_data:
            Rule.objects.create(rule_group=group, **r_data)
            
        for sl_info in sl_data:
            StopLossRule.objects.create(rule_group=group, **sl_info)
            
        for t_info in target_data:
            TargetRule.objects.create(rule_group=group, **t_info)
