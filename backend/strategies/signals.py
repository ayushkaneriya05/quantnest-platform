import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import Strategy, EntryOrderConfig, ExitOrderConfig
from .services import StrategySnapshotService
from risk_management.models import PositionSizingRule, StrategyAutoDisable
from rules_engine.models import RuleGroup, Rule, TimeRule, SpecialEventFilter
from instruments.models import WatchlistInstrument, ExecutionRoute

logger = logging.getLogger(__name__)


def save_checkpoint(strategy_id, initial=False):
    strategy = Strategy.objects.filter(pk=strategy_id).first()
    if not strategy:
        return
    latest = strategy.versions.order_by("-version_number").first()
    if initial:
        if latest:
            return
    elif not strategy.auto_version_enabled:
        return
    snapshot = StrategySnapshotService._serialize_strategy(strategy)
    if latest and latest.config_snapshot == snapshot:
        return
    StrategySnapshotService.create_snapshot(strategy, user=strategy.user,
        change_notes="Initial strategy configuration" if initial else "Auto-save checkpoint")


@receiver(post_save, sender=Strategy)
def create_strategy_configs(sender, instance, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        enabled = instance.auto_version_enabled
        instance.auto_version_enabled = False
        Strategy.objects.filter(pk=instance.pk).update(auto_version_enabled=False)
        for model in (EntryOrderConfig, ExitOrderConfig, PositionSizingRule, TimeRule, SpecialEventFilter):
            model.objects.get_or_create(strategy=instance)
        instance.auto_version_enabled = enabled
        Strategy.objects.filter(pk=instance.pk).update(auto_version_enabled=enabled)
        transaction.on_commit(lambda: save_checkpoint(instance.pk, initial=True))


@receiver(post_save, sender=Strategy)
@receiver(post_save, sender=EntryOrderConfig)
@receiver(post_save, sender=ExitOrderConfig)
@receiver(post_save, sender=TimeRule)
@receiver(post_save, sender=SpecialEventFilter)
@receiver(post_save, sender=RuleGroup)
@receiver(post_save, sender=Rule)
@receiver(post_save, sender=PositionSizingRule)
@receiver(post_save, sender=StrategyAutoDisable)
@receiver(post_save, sender=WatchlistInstrument)
@receiver(post_save, sender=ExecutionRoute)
@receiver(post_delete, sender=RuleGroup)
@receiver(post_delete, sender=Rule)
@receiver(post_delete, sender=StrategyAutoDisable)
@receiver(post_delete, sender=WatchlistInstrument)
@receiver(post_delete, sender=ExecutionRoute)
def auto_create_version(sender, instance, **kwargs):
    if sender is Strategy and kwargs.get("created"):
        return
    if isinstance(instance, Strategy):
        strategy = instance
    elif isinstance(instance, ExecutionRoute):
        strategy = instance.watchlist_instrument.strategy
    elif isinstance(instance, Rule):
        strategy = instance.rule_group.strategy
    else:
        strategy = instance.strategy
    if strategy.auto_version_enabled:
        transaction.on_commit(lambda: save_checkpoint(strategy.pk))


@receiver(m2m_changed, sender=Strategy.tags.through)
def version_tag_changes(sender, instance, action, reverse, **kwargs):
    if not reverse and action in ("post_add", "post_remove", "post_clear") and instance.auto_version_enabled:
        transaction.on_commit(lambda: save_checkpoint(instance.pk))
