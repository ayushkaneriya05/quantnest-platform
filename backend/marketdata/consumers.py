import json
import hashlib
from channels.generic.websocket import AsyncWebsocketConsumer

class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            # Reject anonymous users
            await self.close()
        else:
            await self.accept()
            self.user_group_name = f"user_{user.id}"
            self.subscriptions = set()  # Track all instrument groups subscribed by this user

            # Add user to their private group (optional, for personal notifications)
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)

            await self.send(json.dumps({"status": "connected", "user": user.username}))
            print(f"✅ User {user.username} connected to MarketDataConsumer")

    async def disconnect(self, close_code):
        # Remove user from all subscribed instrument groups
        for group in self.subscriptions:
            await self.channel_layer.group_discard(group, self.channel_name)

        # Remove from personal user group
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

        print(f"❌ User disconnected from MarketDataConsumer")

    async def receive(self, text_data):
        """
        Handle incoming messages from the client.
        Expected message format:
        {
            "type": "subscribe",
            "instrument": "NSE:RELIANCE"
        }
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe":
                instrument = data.get("instrument")
                if instrument:
                    # Hash the instrument name to match broadcaster
                    hashed_instrument = hashlib.sha1(instrument.encode()).hexdigest()

                    # Add to user's subscriptions set
                    self.subscriptions.add(hashed_instrument)

                    # Subscribe user to instrument group
                    await self.channel_layer.group_add(hashed_instrument, self.channel_name)

                    await self.send(json.dumps({"status": "subscribed", "instrument": instrument}))
                    print(f"✅ User subscribed to {instrument}")

            elif message_type == "unsubscribe":
                instrument = data.get("instrument")
                if instrument:
                    hashed_instrument = hashlib.sha1(instrument.encode()).hexdigest()
                    if hashed_instrument in self.subscriptions:
                        self.subscriptions.remove(hashed_instrument)
                        await self.channel_layer.group_discard(hashed_instrument, self.channel_name)
                        await self.send(json.dumps({"status": "unsubscribed", "instrument": instrument}))
                        print(f"⚠️ User unsubscribed from {instrument}")

        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def marketdata_message(self, event):
        """
        Receives broadcasted market data from Channels layer
        and sends it to the WebSocket client.
        """
        try:
            await self.send(json.dumps(event["message"]))
        except Exception as e:
            print(f"Error sending market data: {e}")
