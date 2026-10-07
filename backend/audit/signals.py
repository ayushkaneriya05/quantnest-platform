"""Watch configuration fields only. Order, position and tick updates are excluded."""
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from .services import AuditService, SAFE_FIELDS


def before_save(sender, instance, update_fields=None, raw=False, **kwargs):
    if raw:
        return
    fields = SAFE_FIELDS[sender.__name__]
    if update_fields is not None and not set(update_fields).intersection(fields) and not getattr(instance, "_audit_sensitive_fields", None):
        return
    previous = sender.objects.filter(pk=instance.pk).only(*fields).first() if instance.pk else None
    instance._audit_previous = AuditService.snapshot_instance(previous) if previous else {}
    instance._audit_track_save = True


def after_save(sender, instance, created, raw=False, **kwargs):
    if raw or not getattr(instance, "_audit_track_save", False):
        return
    instance._audit_track_save = False
    old = instance._audit_previous
    new = AuditService.snapshot_instance(instance)
    changed = {key: value for key, value in new.items() if old.get(key) != value}
    sensitive = getattr(instance, "_audit_sensitive_fields", ())
    instance._audit_sensitive_fields = ()
    if not created and not changed and not sensitive:
        return
    action = "CREATE" if created else "UPDATE"
    if sender.__name__ in {"CapitalAllocation", "LiveStrategyAllocation"} and created:
        action = "ALLOCATE"
    if created and sender.__name__ in {"TradingSession", "PaperTradingSession"}:
        action = "DEPLOY" if new.get("status") == "RUNNING" else "CREATE"
    elif sender.__name__ in {"TradingSession", "PaperTradingSession"} and "status" in changed:
        action = {"RUNNING": "RESUME" if old.get("status") in {"PAUSED", "ERROR"} else "DEPLOY",
                  "PAUSED": "PAUSE", "STOPPING": "STOP_REQUESTED", "STOPPED": "STOP"}.get(new["status"], action)
    owner = instance.portfolio.user if sender.__name__ == "CapitalAllocation" else instance.user
    AuditService.log_action(owner, action, instance, old_value={key: old.get(key) for key in changed},
                            new_value=changed, reason=("Credential fields changed: " + ", ".join(sensitive)) if sensitive else getattr(instance, "_audit_reason", ""),
                            actor_name=getattr(instance, "_audit_actor", None))


def before_delete(sender, instance, **kwargs):
    instance._audit_owner = instance.portfolio.user if sender.__name__ == "CapitalAllocation" else instance.user
    # Do not create owned events while that owner is being deleted.
    origin = kwargs.get("origin")
    instance._audit_skip_delete = origin == instance._audit_owner or getattr(origin, "model", None) is type(instance._audit_owner)


def after_delete(sender, instance, **kwargs):
    if instance._audit_skip_delete:
        return
    owner = instance._audit_owner
    action = "DEALLOCATE" if sender.__name__ in {"CapitalAllocation", "LiveStrategyAllocation"} else "DELETE"
    AuditService.log_action(owner, action, instance, old_value=AuditService.snapshot_instance(instance))


from brokers.models import BrokerCredential
from strategies.models import Strategy
from paper_trading.models import CapitalAllocation, PaperAccount, PaperTradingSession
from live_trading.models import LiveStrategyAllocation, TradingSession

for model in (Strategy, BrokerCredential, CapitalAllocation, PaperAccount, PaperTradingSession, LiveStrategyAllocation, TradingSession):
    pre_save.connect(before_save, sender=model, dispatch_uid=f"audit:{model._meta.label}:before")
    post_save.connect(after_save, sender=model, dispatch_uid=f"audit:{model._meta.label}:after")
    pre_delete.connect(before_delete, sender=model, dispatch_uid=f"audit:{model._meta.label}:before_delete")
    post_delete.connect(after_delete, sender=model, dispatch_uid=f"audit:{model._meta.label}:delete")
