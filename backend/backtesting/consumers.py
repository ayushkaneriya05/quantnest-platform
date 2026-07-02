import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class BacktestProgressConsumer(AsyncWebsocketConsumer):
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
        """
        Handles backtest progress update messages.
        Expected event format:
        {
            "type": "backtest.progress",
            "message": {
                "run_id": 123,
                "status": "RUNNING",
                "progress_pct": 45,
                "message": "Processing candles...",
                "timestamp": "2026-05-24T10:30:00Z"
            }
        }
        """
        message = event.get("message")
        if message:
            await self.send(text_data=json.dumps(message))

    async def backtest_completed(self, event):
        """
        Handles backtest completion messages.
        Expected event format:
        {
            "type": "backtest.completed",
            "message": {
                "run_id": 123,
                "status": "COMPLETED",
                "progress_pct": 100,
                "trades_count": 15,
                "message": "Backtest completed successfully"
            }
        }
        """
        message = event.get("message")
        if message:
            await self.send(text_data=json.dumps(message))

    async def backtest_error(self, event):
        """
        Handles backtest error messages.
        Expected event format:
        {
            "type": "backtest.error",
            "message": {
                "run_id": 123,
                "status": "FAILED",
                "error": "Insufficient data for backtest period"
            }
        }
        """
        message = event.get("message")
        if message:
            await self.send(text_data=json.dumps(message))
