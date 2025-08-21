import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject connection if user not authenticated
            await self.close()
        else:
            await self.accept()
            username = self.scope["user"].username
            print(f"✅ User {username} connected to MarketDataConsumer")

            # Each user gets their own private group
            self.user_group_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            # Confirm connection
            await self.send(json.dumps({"status": "connected", "user": username}))

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "subscribe":
            instrument = data.get("instrument")
            if instrument:
                # Subscribe user to instrument updates
                await self.channel_layer.group_add(
                    instrument,
                    self.channel_name
                )
                await self.send(json.dumps({"status": "subscribed", "instrument": instrument}))

    async def marketdata_message(self, event):
        # Broadcast market updates to the client
        await self.send(json.dumps(event["message"]))
