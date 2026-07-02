from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from brokers.models import BrokerCredential
from strategies.models import Strategy

from .services import AuditService


# ── Models to track ──
_TRACKED_MODELS = [Strategy, BrokerCredential]

# Dynamically add signals for live_trading models if available
try:
    from live_trading.models import TradingSession
    _TRACKED_MODELS.append(TradingSession)
except Exception:
    TradingSession = None

try:
    from marketplace.models import MarketplaceListing
    _TRACKED_MODELS.append(MarketplaceListing)
except Exception:
    MarketplaceListing = None


@receiver(pre_save, sender=Strategy)
@receiver(pre_save, sender=BrokerCredential)
def cache_old_entity_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._audit_old_value = AuditService.snapshot_instance(sender.objects.get(pk=instance.pk))
        except sender.DoesNotExist:
            instance._audit_old_value = {}


@receiver(post_save, sender=Strategy)
@receiver(post_save, sender=BrokerCredential)
def log_entity_save(sender, instance, created, **kwargs):
    AuditService.log_action(
        getattr(instance, "user", None),
        "CREATE" if created else "UPDATE",
        instance,
        old_value=getattr(instance, "_audit_old_value", {}),
        new_value=AuditService.snapshot_instance(instance),
    )


@receiver(post_delete, sender=Strategy)
@receiver(post_delete, sender=BrokerCredential)
def log_entity_delete(sender, instance, **kwargs):
    AuditService.log_action(
        getattr(instance, "user", None),
        "DELETE",
        instance,
        old_value=AuditService.snapshot_instance(instance),
        new_value={},
    )


# ── TradingSession signals ──
if TradingSession is not None:
    @receiver(pre_save, sender=TradingSession)
    def cache_old_session_state(sender, instance, **kwargs):
        if instance.pk:
            try:
                instance._audit_old_value = AuditService.snapshot_instance(sender.objects.get(pk=instance.pk))
            except sender.DoesNotExist:
                instance._audit_old_value = {}

    @receiver(post_save, sender=TradingSession)
    def log_session_save(sender, instance, created, **kwargs):
        action = "CREATE" if created else "UPDATE"
        # Map session status to meaningful audit actions
        if not created:
            new_status = getattr(instance, "status", "")
            if new_status == "RUNNING":
                action = "DEPLOY"
            elif new_status == "PAUSED":
                action = "PAUSE"
            elif new_status == "STOPPED":
                action = "STOP"
        AuditService.log_action(
            getattr(instance, "user", None),
            action,
            instance,
            old_value=getattr(instance, "_audit_old_value", {}),
            new_value=AuditService.snapshot_instance(instance),
        )


# ── MarketplaceListing signals ──
if MarketplaceListing is not None:
    @receiver(pre_save, sender=MarketplaceListing)
    def cache_old_listing_state(sender, instance, **kwargs):
        if instance.pk:
            try:
                instance._audit_old_value = AuditService.snapshot_instance(sender.objects.get(pk=instance.pk))
            except sender.DoesNotExist:
                instance._audit_old_value = {}

    @receiver(post_save, sender=MarketplaceListing)
    def log_listing_save(sender, instance, created, **kwargs):
        AuditService.log_action(
            getattr(instance, "creator", None),
            "CREATE" if created else "UPDATE",
            instance,
            old_value=getattr(instance, "_audit_old_value", {}),
            new_value=AuditService.snapshot_instance(instance),
        )
