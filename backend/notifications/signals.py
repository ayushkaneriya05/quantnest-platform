import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.core.cache import cache
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from common.enums import NotificationType, Severity, OrderStatus, StrategyStatus

# Ensure these imports don't fail by avoiding circular dependencies.
# We'll import models inside the receiver or use string-based signals where possible.
from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)

def broadcast_notification(notification):
    """
    Broadcast the notification to the user's specific WebSocket channel.
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"user_notifications_{notification.user_id}",
            {
                "type": "send_notification",
                "notification": {
                    "id": str(notification.id),
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.type,
                    "severity": notification.severity,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                    "data": notification.data
                }
            }
        )

# Listen to all newly created Notifications and broadcast them!
@receiver(post_save, sender=Notification)
def handle_new_notification(sender, instance, created, **kwargs):
    if created:
        broadcast_notification(instance)


# Now, let's create hooks for trading and strategy events.
# We use string referencing to avoid import issues during startup.

@receiver(post_save, sender="live_trading.LiveOrder")
def handle_live_order_notifications(sender, instance, created, **kwargs):
    # Only notify on specific terminal states
    if instance.status == OrderStatus.FILLED:
        tag = instance.order_tag.upper() if instance.order_tag else ""
        notif_type = NotificationType.TRADE_EXECUTED
        severity = Severity.INFO
        title = "Live Trade Executed"
        
        if "SL" in tag or "STOP" in tag:
            notif_type = NotificationType.SL_HIT
            severity = Severity.WARNING
            title = "Live Stop Loss Hit"
        elif "TARGET" in tag or "TP" in tag or "TAKE_PROFIT" in tag:
            notif_type = NotificationType.TARGET_HIT
            title = "Live Target Hit"

        NotificationService.notify(
            user=instance.user,
            title=title,
            message=f"Order for {instance.instrument.symbol} was filled at {instance.average_price}",
            notification_type=notif_type,
            severity=severity,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
    elif instance.status == OrderStatus.REJECTED:
        NotificationService.notify(
            user=instance.user,
            title="Live Order Rejected",
            message=f"Order for {instance.instrument.symbol} was rejected.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.CRITICAL,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )


@receiver(post_save, sender="paper_trading.PaperOrder")
def handle_paper_order_notifications(sender, instance, created, **kwargs):
    if instance.status == OrderStatus.FILLED:
        tag = instance.order_tag.upper() if instance.order_tag else ""
        notif_type = NotificationType.TRADE_EXECUTED
        severity = Severity.INFO
        title = "Paper Trade Executed"
        
        if "SL" in tag or "STOP" in tag:
            notif_type = NotificationType.SL_HIT
            severity = Severity.WARNING
            title = "Paper Stop Loss Hit"
        elif "TARGET" in tag or "TP" in tag or "TAKE_PROFIT" in tag:
            notif_type = NotificationType.TARGET_HIT
            title = "Paper Target Hit"

        NotificationService.notify(
            user=instance.user,
            title=title,
            message=f"Simulated order for {instance.instrument.symbol} was filled.",
            notification_type=notif_type,
            severity=severity,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )
    elif instance.status == OrderStatus.REJECTED:
        NotificationService.notify(
            user=instance.user,
            title="Paper Order Rejected",
            message=f"Simulated order for {instance.instrument.symbol} was rejected.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.WARNING,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )


@receiver(post_save, sender="strategies.Strategy")
def handle_strategy_notifications(sender, instance, created, **kwargs):
    # This might trigger too often if we don't check what changed, 
    # but for simplicity we will check if it's paused. 
    # In a real scenario, we might use a custom signal for circuit breaker.
    if not created and instance.status == StrategyStatus.PAUSED:
        cache_key = f"strategy_paused_notif_{instance.id}"
        if not cache.get(cache_key):
            NotificationService.notify(
                user=instance.user,
                title="Strategy Paused",
                message=f"Your strategy '{instance.name}' has been paused.",
                notification_type=NotificationType.STRATEGY_PAUSED,
                severity=Severity.WARNING,
                strategy=instance,
                data={"strategy_id": str(instance.id)}
            )
            cache.set(cache_key, True, 3600)  # 60 minute cooldown

@receiver(post_save, sender="paper_trading.PaperAccount")
def handle_paper_account_notifications(sender, instance, created, **kwargs):
    if instance.initial_balance > 0:
        threshold = instance.initial_balance * Decimal('0.10')  # 10% remaining
        if instance.margin_available < threshold:
            cache_key = f"risk_alert_paper_{instance.id}"
            if not cache.get(cache_key):
                NotificationService.notify(
                    user=instance.user,
                    title="Risk Alert: Low Margin",
                    message=f"Paper Account '{instance.name}' margin is critically low.",
                    notification_type=NotificationType.RISK_ALERT,
                    severity=Severity.CRITICAL,
                    data={"account_id": str(instance.id), "module": "paper"}
                )
                cache.set(cache_key, True, 86400)  # 24 hour cooldown
