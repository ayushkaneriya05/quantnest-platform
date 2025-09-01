# trading/receivers.py
import json
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver

from .signals import order_status_changed, position_changed

logger = logging.getLogger(__name__)

channel_layer = get_channel_layer()

@receiver(order_status_changed)
def handle_order_status_changed(sender, order, **kwargs):
    """Send order updates to the user’s WebSocket group"""
    try:
        group_name = f"user_{order.account.user.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "order_update",
                "message": {
                    "id": order.id,
                    "status": order.status,
                    "instrument": order.instrument.symbol,
                    "quantity": order.quantity,
                },
            },
        )
        logger.info(f"📡 Sent order update for order {order.id} to {group_name}")
    except Exception as e:
        logger.error(f"❌ Failed to send order update: {e}")


@receiver(position_changed)
def handle_position_changed(sender, position, user_id, **kwargs):
    """Send position updates to the user’s WebSocket group"""
    try:
        group_name = f"user_{user_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "position_update",
                "message": (
                    {
                        "id": position.id,
                        "instrument": position.instrument.symbol,
                        "quantity": position.quantity,
                        "average_price": str(position.average_price),
                    }
                    if hasattr(position, "id")  # when it's a real model
                    else position               # when you send a dict before deletion
                ),
            },
        )
        logger.info(f"📡 Sent position update for {position} to {group_name}")
    except Exception as e:
        logger.error(f"❌ Failed to send position update: {e}")
