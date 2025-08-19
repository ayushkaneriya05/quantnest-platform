# backend/marketdata/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # A user can only connect if they are authenticated
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            await self.accept()
            print(f"User {self.scope['user'].username} connected to MarketDataConsumer")
            # Each user gets their own private channel group
            self.user_group_name = f'user_{self.scope["user"].id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handles messages from the client, e.g., subscribing to an instrument.
        """
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'subscribe':
            instrument = data.get('instrument')
            if instrument:
                # Add user to the instrument-specific group
                await self.channel_layer.group_add(
                    instrument,
                    self.channel_name
                )

    async def marketdata_message(self, event):
        """
        Handler for messages sent from the broadcaster to an instrument group.
        """
        await self.send(text_data=json.dumps(event["message"]))