from users.websocket import AuthSessionConsumerMixin
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ResearchConsumer(AuthSessionConsumerMixin, AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = f"research_{user.pk}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def research_update(self, event):
        await self.send_json(event["data"])
