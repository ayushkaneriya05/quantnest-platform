import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class PaperTradingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Rejected unauthenticated WebSocket connection for Paper Trading")
            await self.close(code=4003)
            return

        self.group_name = f"user_{user.id}_paper"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def trading_update(self, event):
        """Forward the signal payload without changing its shape."""
        message = event.get("message")
        if isinstance(message, dict):
            await self.send(text_data=json.dumps(message))
