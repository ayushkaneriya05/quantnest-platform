import json
from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from rest_framework.renderers import JSONRenderer

from common.enums import NotificationType, OrderStatus

from .models import Notification
from .serializers import NotificationSerializer
from .services import NotificationService


def broadcast_notification(notification):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        notification_data = json.loads(JSONRenderer().render(NotificationSerializer(notification).data))
        async_to_sync(channel_layer.group_send)(
            f"user_notifications_{notification.user_id}",
            {"type": "send_notification", "notification": notification_data},
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Could not broadcast notification %s", notification.pk)


@receiver(post_save, sender=Notification)
def broadcast_after_commit(sender, instance, created, **kwargs):
    if created:
        from django.db import transaction
        transaction.on_commit(lambda: broadcast_notification(instance))


def _capture_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_status = None
        return
    instance._notification_previous_status = sender.objects.filter(pk=instance.pk).values_list("status", "filled_quantity").first()


def _order_status_notification(instance, *, user, module, account_name=None, broker_name=None):
    status = instance.status
    if status not in {
        OrderStatus.PLACED,
        OrderStatus.PARTIAL_FILL,
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    }:
        return

    symbol = instance.instrument.symbol
    side = getattr(instance, "side", "")
    quantity = instance.quantity
    filled = getattr(instance, "filled_quantity", 0)
    price = getattr(instance, "avg_fill_price", None)
    status_title = {
        OrderStatus.PLACED: "submitted",
        OrderStatus.PARTIAL_FILL: "partially filled",
        OrderStatus.FILLED: "filled",
        OrderStatus.REJECTED: "rejected",
        OrderStatus.CANCELLED: "cancelled",
        OrderStatus.EXPIRED: "expired",
    }[status]
    type_by_status = {
        OrderStatus.PLACED: NotificationType.INFO,
        OrderStatus.PARTIAL_FILL: NotificationType.INFO,
        OrderStatus.FILLED: NotificationType.INFO,
        OrderStatus.REJECTED: NotificationType.WARNING,
        OrderStatus.CANCELLED: NotificationType.INFO,
        OrderStatus.EXPIRED: NotificationType.WARNING,
    }
    title = f"{module.title()} order {status_title}: {side} {symbol}"
    details = [f"Order {instance.pk}", f"filled {filled}/{quantity}"]
    if price is not None:
        details.append(f"average fill {price}")
    if account_name:
        details.append(f"account {account_name}")
    if broker_name:
        details.append(f"broker {broker_name}")
    strategy = getattr(instance, "strategy", None)
    if strategy:
        details.append(f"strategy {strategy.name}")
    reason = getattr(instance, "rejection_reason", "") or getattr(instance, "reason", "")
    if status in {OrderStatus.REJECTED, OrderStatus.EXPIRED} and reason:
        details.append(f"reason: {reason}")

    allocation = getattr(instance, "allocation", None)
    broker_credential = getattr(instance, "broker_credential", None)
    data = {
        "module": module,
        "order_id": str(instance.pk),
        "status": status,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "filled_quantity": filled,
        "average_fill_price": str(price) if price is not None else None,
        "strategy_id": str(strategy.pk) if strategy else None,
        "strategy_name": strategy.name if strategy else None,
        "allocation_id": str(allocation.pk) if allocation else None,
        "broker_credential_id": str(broker_credential.pk) if broker_credential else None,
        "account_id": str(instance.account_id) if module == "paper" else None,
        "session_id": str(instance.session_id) if getattr(instance, "session_id", None) else None,
    }
    NotificationService.notify(
        user=user,
        type=type_by_status[status],
        title=title,
        message=" · ".join(details),
        data=data,
        dedupe_key=f"order:{module}:{instance.pk}:{status}:{filled}",
    )


@receiver(pre_save, sender="live_trading.LiveOrder")
def capture_live_order_status(sender, instance, **kwargs):
    _capture_previous_status(sender, instance)


@receiver(post_save, sender="live_trading.LiveOrder")
def notify_live_order_status(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if not created and previous == (instance.status, instance.filled_quantity):
        return
    credential = getattr(instance, "broker_credential", None)
    _order_status_notification(
        instance,
        user=instance.user,
        module="live",
        account_name=getattr(credential, "label", None),
        broker_name=getattr(credential, "broker_name", None),
    )


@receiver(pre_save, sender="paper_trading.PaperOrder")
def capture_paper_order_status(sender, instance, **kwargs):
    _capture_previous_status(sender, instance)


@receiver(post_save, sender="paper_trading.PaperOrder")
def notify_paper_order_status(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if not created and previous == (instance.status, instance.filled_quantity):
        return
    account = instance.account
    _order_status_notification(
        instance,
        user=account.user,
        module="paper",
        account_name=getattr(account, "name", None),
    )


@receiver(post_save, sender="live_trading.TradingSession")
def notify_live_session_error(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if instance.status != "ERROR" or (not created and previous == "ERROR"):
        return
    NotificationService.notify(
        user=instance.user,
        type=NotificationType.CRITICAL,
        title=f"Live strategy error: {instance.strategy.name}",
        message=instance.error_message or "The live session entered an error state.",
        data={"session_id": str(instance.pk), "strategy_id": str(instance.strategy_id), "strategy_name": instance.strategy.name, "module": "live"},
        dedupe_key=f"live-session-error:{instance.pk}:{instance.updated_at.isoformat()}",
    )


@receiver(post_save, sender="paper_trading.PaperTradingSession")
def notify_paper_session_error(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if instance.status != "ERROR" or (not created and previous == "ERROR"):
        return
    NotificationService.notify(
        user=instance.user,
        type=NotificationType.CRITICAL,
        title=f"Paper strategy error: {instance.strategy.name}",
        message=instance.error_message or "The paper session entered an error state.",
        data={"session_id": str(instance.pk), "strategy_id": str(instance.strategy_id), "strategy_name": instance.strategy.name, "module": "paper"},
        dedupe_key=f"paper-session-error:{instance.pk}:{instance.updated_at.isoformat()}",
    )


@receiver(pre_save, sender="live_trading.TradingSession")
def capture_live_session_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_status = None
        return
    instance._notification_previous_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(pre_save, sender="paper_trading.PaperTradingSession")
def capture_paper_session_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_status = None
        return
    instance._notification_previous_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(post_save, sender="paper_trading.PaperAccount")
def notify_paper_low_margin(sender, instance, created, **kwargs):
    if instance.initial_balance <= 0 or instance.margin_available >= instance.initial_balance * Decimal("0.10"):
        return
    NotificationService.notify(
        user=instance.user,
        type=NotificationType.CRITICAL,
        title=f"Low available margin: {instance.name}",
        message=f"Paper account margin is below 10% of its initial balance ({instance.margin_available} remaining).",
        data={"account_id": str(instance.pk), "module": "paper"},
        dedupe_key=f"paper-account-low-margin:{instance.pk}:{instance.updated_at.date().isoformat()}",
    )


@receiver(pre_save, sender="strategies.Strategy")
def capture_strategy_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_status = None
        return
    instance._notification_previous_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(post_save, sender="strategies.Strategy")
def notify_strategy_status(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if created or previous == instance.status or instance.status not in {"ACTIVE", "PAUSED", "ARCHIVED", "DRAFT"}:
        return
    status_label = {
        "ACTIVE": "activated",
        "PAUSED": "paused",
        "ARCHIVED": "archived",
        "DRAFT": "restored to draft",
    }[instance.status]
    type = NotificationType.WARNING if instance.status == "PAUSED" else NotificationType.INFO
    NotificationService.notify(
        user=instance.user,
        type=type,
        title=f"Strategy {status_label}: {instance.name}",
        message=f"Strategy '{instance.name}' is now {instance.status.lower()}.",
        data={"module": "strategy", "strategy_id": str(instance.pk), "strategy_name": instance.name, "status": instance.status},
        dedupe_key=f"strategy-status:{instance.pk}:{instance.status}:{instance.updated_at.isoformat()}",
    )
