import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.dispatch import receiver

from common.channel_serialization import json_safe_channel_data
from common.enums import NotificationType
from notifications.services import NotificationService

from .serializers import OrderSerializer, PositionSerializer
from .signals import order_status_changed, position_changed

logger = logging.getLogger(__name__)


def _broadcast_update(user_id, event_type, data):
    """Publish a committed terminal update to the existing market-data socket group."""
    try:
        channel_layer = get_channel_layer()
    except Exception:
        logger.exception("Could not get Channels layer for terminal %s update", event_type)
        return
    if channel_layer is None:
        logger.warning("No Channels layer configured; dropped terminal %s update", event_type)
        return

    message = {"event_type": event_type, "data": data}

    def send_after_commit():
        try:
            channel_message = json_safe_channel_data(message)
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {"type": event_type.lower(), "message": channel_message},
            )
        except Exception:
            logger.exception("Failed to broadcast terminal %s update for user %s", event_type, user_id)

    transaction.on_commit(send_after_commit)


@receiver(order_status_changed)
def publish_order_update(sender, order, **kwargs):
    _broadcast_update(order.account.user_id, "ORDER_UPDATE", OrderSerializer(order).data)
    status_config = {
        "OPEN": (NotificationType.INFO, "submitted"),
        "COMPLETE": (NotificationType.INFO, "filled"),
        "CANCELLED": (NotificationType.INFO, "cancelled"),
        "REJECTED": (NotificationType.WARNING, "rejected"),
    }
    if order.status not in status_config:
        return
    type, status_label = status_config[order.status]
    symbol = order.instrument.symbol
    message = f"Order {order.pk}: {order.transaction_type} {order.quantity} {symbol} ({order.order_type.lower()})."

    def notify_after_commit():
        NotificationService.notify(
            user_id=order.account.user_id,
            type=type,
            title=f"Manual order {status_label}: {order.transaction_type} {symbol}",
            message=message,
            data={
                "module": "manual",
                "order_id": str(order.pk),
                "symbol": symbol,
                "side": order.transaction_type,
                "quantity": order.quantity,
                "status": order.status,
            },
            dedupe_key=f"manual-order:{order.pk}:{order.status}",
        )

    transaction.on_commit(notify_after_commit)


@receiver(position_changed)
def publish_position_update(sender, position, user_id, **kwargs):
    data = PositionSerializer(position).data if hasattr(position, "_meta") else position
    _broadcast_update(user_id, "POSITION_UPDATE", data)
