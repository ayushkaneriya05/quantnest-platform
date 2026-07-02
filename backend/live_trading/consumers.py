import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class LiveTradingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Rejected unauthenticated WebSocket connection for Live Trading")
            await self.close(code=4003)
            return

        self.group_name = f"user_{user.id}_live"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"User {user.id} connected to live trading WebSocket stream")

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def live_update(self, event):
        """
        Sends an update payload to the connected client.
        Expected event format:
        {
            "type": "live.update",
            "message": {
                "event_type": "ORDER_UPDATE" | "POSITION_UPDATE" | "SESSION_UPDATE" | "EXECUTION_LOG",
                "data": {...}
            }
        }
        """
        message = event.get("message")
        if message:
            await self.send(text_data=json.dumps(message))
