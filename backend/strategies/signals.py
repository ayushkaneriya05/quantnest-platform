import logging
from django.db import transaction
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Strategy
from .services import StrategySnapshotService

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
def version_strategy_change(sender, instance, created, **kwargs):
    if created or instance.auto_version_enabled:
        transaction.on_commit(lambda: save_checkpoint(instance.pk, initial=created))


@receiver(m2m_changed, sender=Strategy.tags.through)
def version_tag_changes(sender, instance, action, reverse, **kwargs):
    if not reverse and action in ("post_add", "post_remove", "post_clear") and instance.auto_version_enabled:
        transaction.on_commit(lambda: save_checkpoint(instance.pk))
