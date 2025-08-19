# backend/marketdata/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for clients subscribing to market data.
    """
    async def connect(self):
        # Add the connection to the 'marketdata' group
        symbol = self.scope.get("url_route", {}).get("kwargs", {}).get("symbol")
if symbol:
    await self.channel_layer.group_add(f"market_{symbol}", self.channel_name)
else:
    await self.channel_layer.group_add("marketdata", self.channel_name)
await self.accept()

    async def disconnect(self, close_code):
        # Remove the connection from the 'marketdata' group
        await self.channel_layer.symbol = self.scope.get("url_route", {}).get("kwargs", {}).get("symbol")
if symbol:
    await self.channel_layer.group_discard(f"market_{symbol}", self.channel_name)
else:
    await self.channel_layer.group_discard("marketdata", self.channel_name)

    async def market_data_message(self, event):
        """
        Receives messages from the channel layer group and forwards
        them to the connected WebSocket client.
        """
        message = event["message"]
        await self.send(text_data=json.dumps(message))
