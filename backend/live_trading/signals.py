from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.channels import publish_trading_update
from .models import LiveOrder, LivePosition, TradingSession
from .serializers import LiveOrderSerializer, LivePositionSerializer


@receiver(post_save, sender=LiveOrder)
def publish_live_order_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.user_id}_live", "ORDER_UPDATE", LiveOrderSerializer(instance).data)


@receiver(post_save, sender=LivePosition)
def publish_live_position_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.user_id}_live", "POSITION_UPDATE", LivePositionSerializer(instance).data)


@receiver(post_delete, sender=LivePosition)
def publish_live_position_delete(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.user_id}_live", "POSITION_UPDATE", {
        "id": instance.id,
        "allocation_id": instance.allocation_id,
        "instrument": instance.instrument_id,
        "deleted": True,
    })


@receiver(post_save, sender=TradingSession)
def publish_live_session_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.user_id}_live", "SESSION_UPDATE", {
        "id": instance.id,
        "status": instance.status,
    })
