# backend/trading/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import PaperOrder, AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(pre_save, sender=PaperOrder)
def _capture_old_order_state(sender, instance, **kwargs):
    """
    Store old status on instance for post_save comparison.
    """
    if not instance.pk:
        instance._old_state = None
        return
    try:
        old = PaperOrder.objects.get(pk=instance.pk)
        instance._old_state = {
            "status": old.status,
            "price": str(old.price) if old.price is not None else None,
            "qty": old.qty,
            "trigger_price": str(old.trigger_price) if old.trigger_price is not None else None,
            "is_slm": old.is_slm,
            "stop_trigger_price": str(old.stop_trigger_price) if old.stop_trigger_price is not None else None,
        }
    except PaperOrder.DoesNotExist:
        instance._old_state = None

@receiver(post_save, sender=PaperOrder)
def audit_order_changes(sender, instance: PaperOrder, created, **kwargs):
    """
    Create AuditLog entries for create / modify / cancel events.
    """
    user = getattr(instance, "user", None)
    if created:
        AuditLog.objects.create(order=instance, action=AuditLog.ACTION_CREATED, performed_by=user, details={
            "symbol": instance.symbol,
            "side": instance.side,
            "qty": instance.qty,
            "order_type": instance.order_type,
            "price": str(instance.price) if instance.price is not None else None,
            "trigger_price": str(instance.trigger_price) if instance.trigger_price is not None else None,
            "is_slm": instance.is_slm,
            "stop_trigger_price": str(instance.stop_trigger_price) if instance.stop_trigger_price is not None else None,
            "oco_group": instance.oco_group,
        })
        return

    old = getattr(instance, "_old_state", None)
    # If we have old state, compare
    if old:
        # status change
        if old.get("status") != instance.status:
            # cancelled
            if instance.status == PaperOrder.STATUS_CANCELLED:
                AuditLog.objects.create(order=instance, action=AuditLog.ACTION_CANCELLED, performed_by=user, details={
                    "old_status": old.get("status")
                })
            # executed
            if instance.status == PaperOrder.STATUS_FILLED:
                AuditLog.objects.create(order=instance, action=AuditLog.ACTION_EXECUTED, performed_by=user, details={
                    "filled_qty": instance.filled_qty,
                    "avg_fill_price": str(instance.avg_fill_price) if instance.avg_fill_price else None
                })
        # price changed or qty changed
        changes = {}
        if old.get("price") != (str(instance.price) if instance.price is not None else None):
            changes["price_old"] = old.get("price")
            changes["price_new"] = str(instance.price) if instance.price is not None else None
        if old.get("qty") != instance.qty:
            changes["qty_old"] = old.get("qty")
            changes["qty_new"] = instance.qty
        if old.get("trigger_price") != (str(instance.trigger_price) if instance.trigger_price is not None else None):
            changes["trigger_old"] = old.get("trigger_price")
            changes["trigger_new"] = str(instance.trigger_price) if instance.trigger_price is not None else None
        if changes:
            AuditLog.objects.create(order=instance, action=AuditLog.ACTION_MODIFIED, performed_by=user, details=changes)
