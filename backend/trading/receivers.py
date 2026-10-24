from django.db import transaction
from django.dispatch import receiver

from common.channels import publish_trading_update
from common.enums import NotificationType, TerminalOrderStatus
from notifications.services import NotificationService

from .serializers import OrderSerializer
from .signals import order_status_changed, position_changed


@receiver(order_status_changed)
def publish_order_update(sender, order, **kwargs):
    from .models import Account
    from .services import TradingOrderService
    account = Account.objects.get(pk=order.account_id)
    reserved = TradingOrderService.pending_cash(account)
    payload = dict(OrderSerializer(order).data)
    payload['account_snapshot'] = {'balance': str(account.balance), 'margin': str(account.margin),
        'reserved_cash': str(reserved), 'available_balance': str(max(account.balance - account.margin - reserved, 0)),
        'realized_pnl': str(account.realized_pnl), 'charges_paid': str(account.charges_paid)}
    publish_trading_update(f"user_{account.user_id}", "ORDER_UPDATE", payload)
    status_config = {
        TerminalOrderStatus.OPEN: (NotificationType.INFO, "submitted"),
        TerminalOrderStatus.COMPLETE: (NotificationType.INFO, "filled"),
        TerminalOrderStatus.CANCELLED: (NotificationType.INFO, "cancelled"),
        TerminalOrderStatus.REJECTED: (NotificationType.WARNING, "rejected"),
    }
    if order.status not in status_config:
        return
    type, status_label = status_config[order.status]
    name = order.instrument.name
    message = f"Order {order.pk}: {order.transaction_type} {order.quantity} {name} ({order.order_type.lower()})."

    def notify_after_commit():
        NotificationService.notify(
            user_id=order.account.user_id,
            type=type,
            title=f"Manual order {status_label}: {order.transaction_type} {name}",
            message=message,
            data={
                "module": "manual",
                "order_id": str(order.pk),
                "symbol": order.instrument.sym_ticker,
                "side": order.transaction_type,
                "quantity": order.quantity,
                "status": order.status,
            },
            dedupe_key=f"manual-order:{order.pk}:{order.status}",
        )

    transaction.on_commit(notify_after_commit, robust=True)


@receiver(position_changed)
def publish_position_update(sender, position_data: dict, user_id: int, **kwargs):
    publish_trading_update(f"user_{user_id}", "POSITION_UPDATE", position_data)
