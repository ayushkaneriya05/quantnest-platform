import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.channel_serialization import json_safe_channel_data
from .models import PaperOrder, PaperPosition
from .serializers import PaperOrderSerializer, PaperPositionSerializer

logger = logging.getLogger(__name__)


def _broadcast_update(user_id, event_type, data):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    def send_after_commit():
        try:
            channel_message = json_safe_channel_data({"event_type": event_type, "data": data})
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}_paper",
                {
                    "type": "trading.update",
                    "message": channel_message,
                },
            )
        except Exception:
            logger.exception("Failed to broadcast paper %s update for user %s", event_type, user_id)

    transaction.on_commit(send_after_commit)


@receiver(post_save, sender=PaperOrder)
def publish_paper_order_update(sender, instance, **kwargs):
    _broadcast_update(instance.account.user_id, "ORDER_UPDATE", PaperOrderSerializer(instance).data)


@receiver(post_save, sender=PaperPosition)
def publish_paper_position_update(sender, instance, **kwargs):
    _broadcast_update(instance.account.user_id, "POSITION_UPDATE", PaperPositionSerializer(instance).data)


@receiver(post_delete, sender=PaperPosition)
def publish_paper_position_delete(sender, instance, **kwargs):
    payload = {
        "id": instance.id,
        "account": instance.account_id,
        "strategy": instance.strategy_id,
        "instrument": instance.instrument_id,
        "deleted": True,
    }
    _broadcast_update(instance.account.user_id, "POSITION_UPDATE", payload)

