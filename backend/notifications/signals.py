import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.core.cache import cache
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from common.enums import NotificationType, Severity, OrderStatus, StrategyStatus
from common.cache_keys import CacheKeys

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
    cache_key = CacheKeys.NOTIF_LIVE_ORDER.format(order_id=instance.id, status=instance.status)
    if cache.get(cache_key):
        return

    # Only notify on specific terminal states
    if instance.status == OrderStatus.FILLED:
        notif_type = NotificationType.TRADE_EXECUTED
        severity = Severity.INFO
        title = "Live Trade Executed"
        
        if instance.order_type in ["STOP_MARKET", "STOP_LIMIT"]:
            notif_type = NotificationType.SL_HIT
            severity = Severity.WARNING
            title = "Live Stop Loss Hit"
        NotificationService.notify(
            user=instance.user,
            title=title,
            message=f"Order for {instance.instrument.symbol} was filled at {instance.avg_fill_price}",
            notification_type=notif_type,
            severity=severity,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.REJECTED:
        NotificationService.notify(
            user=instance.user,
            title="Live Order Rejected",
            message=f"Order for {instance.instrument.symbol} was rejected.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.CRITICAL,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.CANCELLED:
        NotificationService.notify(
            user=instance.user,
            title="Live Order Cancelled",
            message=f"Order for {instance.instrument.symbol} was cancelled.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.WARNING,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.EXPIRED:
        NotificationService.notify(
            user=instance.user,
            title="Live Order Expired",
            message=f"Order for {instance.instrument.symbol} expired before execution.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.WARNING,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.PARTIAL_FILL:
        NotificationService.notify(
            user=instance.user,
            title="Live Order Partially Filled",
            message=f"Order for {instance.instrument.symbol} was partially filled.",
            notification_type=NotificationType.TRADE_EXECUTED,
            severity=Severity.INFO,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "live"}
        )
        cache.set(cache_key, True, 86400)


@receiver(post_save, sender="paper_trading.PaperOrder")
def handle_paper_order_notifications(sender, instance, created, **kwargs):
    cache_key = CacheKeys.NOTIF_PAPER_ORDER.format(order_id=instance.id, status=instance.status)
    if cache.get(cache_key):
        return

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
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.REJECTED:
        NotificationService.notify(
            user=instance.user,
            title="Paper Order Rejected",
            message=f"Simulated order for {instance.instrument.symbol} was rejected.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.WARNING,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.CANCELLED:
        NotificationService.notify(
            user=instance.user,
            title="Paper Order Cancelled",
            message=f"Simulated order for {instance.instrument.symbol} was cancelled.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.EXPIRED:
        NotificationService.notify(
            user=instance.user,
            title="Paper Order Expired",
            message=f"Simulated order for {instance.instrument.symbol} expired before execution.",
            notification_type=NotificationType.STRATEGY_ERROR,
            severity=Severity.WARNING,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )
        cache.set(cache_key, True, 86400)
    elif instance.status == OrderStatus.PARTIAL_FILL:
        NotificationService.notify(
            user=instance.user,
            title="Paper Order Partially Filled",
            message=f"Simulated order for {instance.instrument.symbol} was partially filled.",
            notification_type=NotificationType.TRADE_EXECUTED,
            severity=Severity.INFO,
            data={"order_id": str(instance.id), "symbol": instance.instrument.symbol, "module": "paper"}
        )
        cache.set(cache_key, True, 86400)


@receiver(post_save, sender="live_trading.TradingSession")
def handle_live_session_notifications(sender, instance, created, **kwargs):
    if instance.status != "ERROR":
        return
    cache_key = CacheKeys.NOTIF_LIVE_SESSION_ERROR.format(session_id=instance.id, updated_at=instance.updated_at)
    if cache.get(cache_key):
        return
    NotificationService.notify(
        user=instance.user,
        title="Live Strategy Error",
        message=instance.error_message or f"Live session for '{instance.strategy.name}' entered error state.",
        notification_type=NotificationType.STRATEGY_ERROR,
        severity=Severity.CRITICAL,
        strategy=instance.strategy,
        data={"session_id": str(instance.id), "module": "live"}
    )
    cache.set(cache_key, True, 86400)


@receiver(post_save, sender="paper_trading.PaperTradingSession")
def handle_paper_session_notifications(sender, instance, created, **kwargs):
    if instance.status != "ERROR":
        return
    cache_key = CacheKeys.NOTIF_PAPER_SESSION_ERROR.format(session_id=instance.id, updated_at=instance.updated_at)
    if cache.get(cache_key):
        return
    NotificationService.notify(
        user=instance.user,
        title="Paper Strategy Error",
        message=instance.error_message or f"Paper session for '{instance.strategy.name}' entered error state.",
        notification_type=NotificationType.STRATEGY_ERROR,
        severity=Severity.CRITICAL,
        strategy=instance.strategy,
        data={"session_id": str(instance.id), "module": "paper"}
    )
    cache.set(cache_key, True, 86400)


@receiver(post_save, sender="paper_trading.PaperAccount")
def handle_paper_account_notifications(sender, instance, created, **kwargs):
    if instance.initial_balance > 0:
        threshold = instance.initial_balance * Decimal('0.10')  # 10% remaining
        if instance.margin_available < threshold:
            cache_key = CacheKeys.NOTIF_RISK_ALERT_PAPER.format(account_id=instance.id)
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


@receiver(post_save, sender="risk_management.RiskViolation")
def handle_risk_violation_notifications(sender, instance, created, **kwargs):
    """Safety net: ensure RiskViolation records created outside service layer still trigger notifications."""
    if not created:
        return
    cache_key = CacheKeys.NOTIF_RISK_VIOLATION.format(violation_id=instance.id)
    if cache.get(cache_key):
        return
    # We check if a matching notification was created in the last 5 seconds.
    from django.utils import timezone
    from datetime import timedelta
    recent_cutoff = timezone.now() - timedelta(seconds=5)
    already_notified = Notification.objects.filter(
        user=instance.user,
        type=NotificationType.RISK_ALERT,
        created_at__gte=recent_cutoff,
        data__violation_type=instance.violation_type,
    ).exists()
    if not already_notified:
        NotificationService.notify(
            user=instance.user,
            title="Risk Violation Detected",
            message=instance.message or "A risk violation was recorded.",
            notification_type=NotificationType.RISK_ALERT,
            severity=instance.severity or Severity.WARNING,
            strategy=instance.strategy,
            data={"violation_type": instance.violation_type, "action_taken": instance.action_taken}
        )
    cache.set(cache_key, True, 86400)
