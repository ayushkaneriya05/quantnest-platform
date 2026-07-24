from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Strategy, EntryOrderConfig, ReEntryRule, ExitOrderConfig, StrategyVersion
from risk_management.models import PositionSizingRule, StrategyAutoDisable
from rules_engine.models import RuleGroup, Rule, TimeRule, SpecialEventFilter
from .services import StrategySnapshotService
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Strategy)
def create_strategy_configs(sender, instance, created, **kwargs):
    if created:
        EntryOrderConfig.objects.create(strategy=instance)
        ReEntryRule.objects.create(strategy=instance)
        ExitOrderConfig.objects.create(strategy=instance)
        PositionSizingRule.objects.create(strategy=instance)

@receiver(post_save, sender=Strategy)
@receiver(post_save, sender=EntryOrderConfig)
@receiver(post_save, sender=ReEntryRule)
@receiver(post_save, sender=ExitOrderConfig)
@receiver(post_save, sender=TimeRule)
@receiver(post_save, sender=SpecialEventFilter)
@receiver(post_save, sender=RuleGroup)
@receiver(post_save, sender=Rule)
@receiver(post_save, sender=PositionSizingRule)
@receiver(post_save, sender=StrategyAutoDisable)
@receiver(post_delete, sender=RuleGroup)
@receiver(post_delete, sender=Rule)
@receiver(post_delete, sender=StrategyAutoDisable)
def auto_create_version(sender, instance, **kwargs):
    """
    Automatically create a version snapshot on save/delete, with debouncing.
    """
    # 1. Resolve strategy instance
    strategy = None
    if isinstance(instance, Strategy):
        strategy = instance
    elif hasattr(instance, 'strategy'):
        strategy = instance.strategy
    elif hasattr(instance, 'rule_group') and instance.rule_group:
        strategy = instance.rule_group.strategy
    
    if not strategy:
        return
        
    # Skip if strategy is just being created (kwargs.get('created') is True only for post_save)
    if sender == Strategy and kwargs.get('created', False):
        return

    # 2. Update cache for the execution engine immediately, independent of versioning.
    try:
        cache.set(f"strategy_config_{strategy.id}", strategy.to_execution_dict(), timeout=None)
        logger.info(f"Updated execution cache for strategy {strategy.id}")
    except Exception as e:
        logger.error(f"Failed to update cache for strategy {strategy.id}: {e}")

    # 3. Check if auto-versioning is enabled
    if not strategy.auto_version_enabled:
        return

    # 4. Check last version time (Debounce for snapshots)
    # Reduced to 10 seconds for easier testing and more frequent checkpoints
    last_version = strategy.versions.order_by('-created_at').first()
    
    if last_version:
        time_since_last = timezone.now() - last_version.created_at
        if time_since_last < timedelta(seconds=10):
            return

    # 5. Create Snapshot
    try:
        StrategySnapshotService.create_snapshot(
            strategy, 
            change_notes="Auto-save checkpoint"
        )
    except Exception as e:
        logger.error(f"Failed to auto-version strategy {strategy.id}: {e}")
