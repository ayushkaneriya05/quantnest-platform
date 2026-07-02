from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PaperOrder, PaperPosition, PaperTrade
from .serializers import PaperOrderSerializer, PaperPositionSerializer


def _push_user_update(user_id, event_type, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": event_type,
            "message": payload,
        },
    )


@receiver(post_save, sender=PaperOrder)
def publish_paper_order_update(sender, instance, **kwargs):
    _push_user_update(instance.account.user_id, "order.update", PaperOrderSerializer(instance).data)


@receiver(post_save, sender=PaperPosition)
def publish_paper_position_update(sender, instance, **kwargs):
    _push_user_update(instance.account.user_id, "position.update", PaperPositionSerializer(instance).data)


@receiver(post_delete, sender=PaperPosition)
def publish_paper_position_delete(sender, instance, **kwargs):
    payload = {
        "id": instance.id,
        "account": instance.account_id,
        "strategy": instance.strategy_id,
        "instrument": instance.instrument_id,
        "instrument_symbol": getattr(instance.instrument, "symbol", None),
        "deleted": True,
    }
    _push_user_update(instance.account.user_id, "position.update", payload)


@receiver(post_save, sender=PaperTrade)
def publish_paper_trade_completed(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from gamification.services import GamificationService
        from platform_events.services import ActivityService, DomainEventService
        from reputation.models import TradingProof

        user = instance.account.user
        event = DomainEventService.emit(
            "TRADE_COMPLETED",
            user=user,
            source=instance,
            source_app="paper_trading",
            payload={
                "symbol": getattr(instance.instrument, "sym_ticker", ""),
                "net_pnl": str(instance.net_pnl),
                "pnl_pct": str(instance.pnl_pct),
                "strategy": instance.strategy_id,
            },
        )
        TradingProof.objects.get_or_create(
            user=user,
            proof_type="PAPER_VERIFIED",
            source_model="PaperTrade",
            source_id=str(instance.id),
            defaults={"status": "VERIFIED", "metadata": {"net_pnl": str(instance.net_pnl), "pnl_pct": str(instance.pnl_pct)}},
        )
        ActivityService.create(
            user,
            "VERIFIED_TRADE",
            "Completed a verified paper trade",
            summary=f"{getattr(instance.instrument, 'sym_ticker', '')} trade completed",
            target=instance,
            domain_event=event,
            strategy=instance.strategy,
            visibility="PRIVATE",
            metadata={"proof_type": "PAPER_VERIFIED"},
        )
        GamificationService.grant_xp(user, "TRADE_COMPLETED", 10, source=instance, metadata={"verified": True})
    except Exception:
        pass
