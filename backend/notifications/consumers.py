import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            logger.warning("WebSocket unauthorized connection attempt")
            await self.close(code=4001)
            return

        self.user_group_name = f'user_notifications_{user.id}'

        # Join the user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for user {user.id}")
        
        # Send a connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notifications'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for group {self.user_group_name}")

    async def receive(self, text_data):
        # We don't expect the client to send much here, mostly a one-way push.
        pass

    async def send_notification(self, event):
        """
        Handler for the 'send_notification' event.
        Broadcasts the notification data to the WebSocket.
        """
        notification_data = event.get('notification', {})
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': notification_data
        }))
