from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .signals import order_status_changed, position_changed
from .serializers import OrderSerializer, PositionSerializer

@receiver(order_status_changed)
def broadcast_order_update(sender, **kwargs):
    """
    Receives the order_status_changed signal and broadcasts the update.
    """
    order = kwargs.get('order')
    if not order:
        return

    user_id = order.account.user.id
    group_name = f"user_{user_id}"
    channel_layer = get_channel_layer()
    
    serializer = OrderSerializer(order)
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "order.update",  # Custom event type for the consumer
            "message": serializer.data
        }
    )

@receiver(position_changed)
def broadcast_position_update(sender, **kwargs):
    """
    Receives the position_changed signal and broadcasts the update.
    """
    position = kwargs.get('position')
    user_id = kwargs.get('user_id')

    if not position or not user_id:
        return

    group_name = f"user_{user_id}"
    channel_layer = get_channel_layer()

    # Handle the case where the position was closed (and is now a dict)
    if isinstance(position, dict) and position.get('quantity') == 0:
        message = position
    else:
        serializer = PositionSerializer(position)
        message = serializer.data

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "position.update",  # Custom event type for the consumer
            "message": message
        }
    )
