import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import LiveOrder, LivePosition, TradingSession
from .serializers import LiveOrderSerializer, LivePositionSerializer

logger = logging.getLogger(__name__)


def _broadcast_update(user_id, event_type, data):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    event = {
        "type": "trading.update",
        "message": {"event_type": event_type, "data": data},
    }

    def send_after_commit():
        try:
            async_to_sync(channel_layer.group_send)(f"user_{user_id}_live", event)
        except Exception:
            logger.exception("Failed to broadcast live %s update for user %s", event_type, user_id)

    transaction.on_commit(send_after_commit)


@receiver(post_save, sender=LiveOrder)
def publish_live_order_update(sender, instance, **kwargs):
    _broadcast_update(instance.user_id, "ORDER_UPDATE", LiveOrderSerializer(instance).data)


@receiver(post_save, sender=LivePosition)
def publish_live_position_update(sender, instance, **kwargs):
    _broadcast_update(instance.user_id, "POSITION_UPDATE", LivePositionSerializer(instance).data)


@receiver(post_delete, sender=LivePosition)
def publish_live_position_delete(sender, instance, **kwargs):
    _broadcast_update(instance.user_id, "POSITION_UPDATE", {
        "id": instance.id,
        "allocation_id": instance.allocation_id,
        "instrument": instance.instrument_id,
        "deleted": True,
    })


@receiver(post_save, sender=TradingSession)
def publish_live_session_update(sender, instance, **kwargs):
    _broadcast_update(instance.user_id, "SESSION_UPDATE", {
        "id": instance.id,
        "status": instance.status,
    })
