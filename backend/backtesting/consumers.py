from users.websocket import AuthSessionConsumerMixin
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class BacktestProgressConsumer(AuthSessionConsumerMixin, AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time backtest progress updates.
    Clients can subscribe to receive progress updates as they happen.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Rejected unauthenticated WebSocket connection for Backtest Progress")
            await self.close(code=4003)
            return

        self.user_id = user.id
        self.group_name = f"user_{user.id}_backtest"
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"User {user.id} connected to backtest progress WebSocket stream")

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def backtest_progress(self, event):
        """Forward each backtest event's message to the authenticated user."""
        message = event.get("message")
        if message:
            await self.send(text_data=json.dumps(message))

    backtest_completed = backtest_progress
    backtest_error = backtest_progress
