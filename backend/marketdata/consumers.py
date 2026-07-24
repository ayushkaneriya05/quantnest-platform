import json
import re

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .live_feed import LiveMarketDataRegistry
from .streaming import MarketDataStreamer
from .services import MarketDataService


add_client_subscription = sync_to_async(
    LiveMarketDataRegistry.add_client_subscription,
    thread_sensitive=True,
)
remove_client_subscription = database_sync_to_async(
    LiveMarketDataRegistry.remove_client_subscription,
    thread_sensitive=True,
)
get_cached_quote = sync_to_async(MarketDataStreamer.get_cached_quote, thread_sensitive=True)
get_live_quote_from_fyers = sync_to_async(MarketDataService.get_live_quote_from_fyers, thread_sensitive=True)


class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        await self.accept()
        self.user_group_name = f"user_{user.id}"
        self.subscriptions = {}

        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.send(json.dumps({"status": "connected", "user": user.username}))

    async def disconnect(self, close_code):
        if hasattr(self, "subscriptions"):
            for group, instrument in self.subscriptions.items():
                await self.channel_layer.group_discard(group, self.channel_name)
                await remove_client_subscription(instrument)

        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self.send(json.dumps({"type": "pong"}))
                return

            instrument = data.get("instrument")
            if not instrument:
                return

            normalized_instrument = MarketDataStreamer.normalize_symbol(instrument)
            group_name = re.sub(r"[^a-zA-Z0-9\-_.]", "_", normalized_instrument)

            if message_type == "subscribe":
                if group_name not in self.subscriptions:
                    self.subscriptions[group_name] = normalized_instrument
                    await self.channel_layer.group_add(group_name, self.channel_name)
                    await add_client_subscription(normalized_instrument)
                await self.send(json.dumps({"status": "subscribed", "instrument": normalized_instrument}))

                # Immediate Push: Send the last known price instantly
                cached_quote = await get_cached_quote(normalized_instrument)
                if not cached_quote:
                    cached_quote = await get_live_quote_from_fyers(normalized_instrument)
                    
                if cached_quote:
                    await self.send(json.dumps({
                        "type": "tick",
                        "symbol": normalized_instrument,
                        "data": cached_quote
                    }))
            elif message_type == "unsubscribe" and group_name in self.subscriptions:
                original_instrument = self.subscriptions.pop(group_name)
                await self.channel_layer.group_discard(group_name, self.channel_name)
                await remove_client_subscription(original_instrument)
                await self.send(json.dumps({"status": "unsubscribed", "instrument": normalized_instrument}))
        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as exc:
            await self.send(json.dumps({"error": str(exc)}))

    async def marketdata_message(self, event):
        await self.send(json.dumps(event["message"]))

    async def order_update(self, event):
        message = event.get("message")
        if not isinstance(message, dict):
            return
        message["type"] = "order_update"
        await self.send(text_data=json.dumps(message))

    async def position_update(self, event):
        message = event.get("message")
        if not isinstance(message, dict):
            return
        message["type"] = "position_update"
        await self.send(text_data=json.dumps(message))
