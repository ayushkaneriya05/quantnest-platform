from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LiveOrder, LivePosition
from .serializers import LiveOrderSerializer, LivePositionSerializer


def _broadcast(user_id, payload):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(f"user_{user_id}", payload)


@receiver(post_save, sender=LiveOrder)
def publish_live_order_update(sender, instance, **kwargs):
    _broadcast(instance.user_id, {"type": "order.update", "data": LiveOrderSerializer(instance).data})


@receiver(post_save, sender=LivePosition)
def publish_live_position_update(sender, instance, **kwargs):
    _broadcast(instance.user_id, {"type": "position.update", "data": LivePositionSerializer(instance).data})

