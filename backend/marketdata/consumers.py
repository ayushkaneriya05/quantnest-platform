# backend/marketdata/consumers.py
import json
import re
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer


class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # ⬇️ ensure the in-process broadcaster is running
        # try:
        #     await ensure_broadcaster_running()
        # except Exception as e:
        #     # non-fatal; you still can accept the socket, but log it
        #     print(f"Broadcaster start failed: {e}")

        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        await self.accept()
        self.user_group_name = f"user_{user.id}"
        self.subscriptions = set()

        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.send(json.dumps({"status": "connected", "user": user.username}))
        print(f"✅ User {user.username} connected to MarketDataConsumer")

    async def disconnect(self, close_code):
        for group in self.subscriptions:
            await self.channel_layer.group_discard(group, self.channel_name)

        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        print("❌ User disconnected from MarketDataConsumer")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            instrument = data.get("instrument")
            if not instrument:
                return

            # same sanitization as broadcaster
            group_name = re.sub(r"[^a-zA-Z0-9\-_.]", "_", instrument)

            if message_type == "subscribe":
                self.subscriptions.add(group_name)
                await self.channel_layer.group_add(group_name, self.channel_name)
                await self.send(json.dumps({"status": "subscribed", "instrument": instrument}))
                print(f"✅ User subscribed to {instrument}")

            elif message_type == "unsubscribe":
                if group_name in self.subscriptions:
                    self.subscriptions.remove(group_name)
                    await self.channel_layer.group_discard(group_name, self.channel_name)
                    await self.send(json.dumps({"status": "unsubscribed", "instrument": instrument}))
                    print(f"⚠️ User unsubscribed from {instrument}")

        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def marketdata_message(self, event):
        try:
            # event["message"] already has type="tick"
            # which your frontend expects
            await self.send(json.dumps(event["message"]))
        except Exception as e:
            print(f"Error sending market data: {e}")

    async def order_update(self, event):
        """Handles 'order.update' events from the signal receiver."""
        message = event["message"]
        message['type'] = 'order_update'  # Add type for the frontend to parse
        await self.send(text_data=json.dumps(message))

    async def position_update(self, event):
        """Handles 'position.update' events from the signal receiver."""
        message = event["message"]
        message['type'] = 'position_update' # Add type for the frontend to parse
        await self.send(text_data=json.dumps(message))