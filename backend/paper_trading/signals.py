from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from common.channels import publish_trading_update
from .models import PaperOrder, PaperPosition, PaperTradingSession
from .serializers import PaperOrderSerializer, PaperPositionSerializer


@receiver(post_save, sender=PaperTradingSession)
@receiver(post_delete, sender=PaperTradingSession)
def publish_paper_session_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.user_id}_paper", "SESSION_UPDATE", {
        "id": instance.id, "status": instance.status,
    })


@receiver(post_save, sender=PaperOrder)
def publish_paper_order_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.account.user_id}_paper", "ORDER_UPDATE", PaperOrderSerializer(instance).data)


@receiver(post_save, sender=PaperPosition)
def publish_paper_position_update(sender, instance, **kwargs):
    publish_trading_update(f"user_{instance.account.user_id}_paper", "POSITION_UPDATE", PaperPositionSerializer(instance).data)


@receiver(post_delete, sender=PaperPosition)
def publish_paper_position_delete(sender, instance, **kwargs):
    payload = {
        "id": instance.id,
        "account": instance.account_id,
        "strategy": instance.strategy_id,
        "instrument": instance.instrument_id,
        "deleted": True,
    }
    publish_trading_update(f"user_{instance.account.user_id}_paper", "POSITION_UPDATE", payload)

