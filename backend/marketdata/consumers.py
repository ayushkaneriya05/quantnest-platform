# backend/marketdata/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        # require authentication for trading endpoints
        if user is None or user.is_anonymous:
            await self.close()
            return
        # add user to user group for private messages
        await self.channel_layer.group_add(f"user_{user.id}", self.channel_name)
        self.subscriptions = set()
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if user and not user.is_anonymous:
            await self.channel_layer.group_discard(f"user_{user.id}", self.channel_name)
        for sym in list(getattr(self, "subscriptions", [])):
            await self.channel_layer.group_discard(f"symbol_{sym}", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        action = data.get("action")
        if action == "subscribe":
            symbol = data.get("symbol")
            if not symbol:
                return
            # basic per-connection cap
            if len(self.subscriptions) >= 30 and symbol not in self.subscriptions:
                await self.send(json.dumps({"type":"error","message":"subscription limit reached"}))
                return
            await self.channel_layer.group_add(f"symbol_{symbol}", self.channel_name)
            self.subscriptions.add(symbol)
            # also mark active_symbols in redis for building candles
            import redis, os
            r = redis.Redis.from_url(os.getenv("REDIS_URL","redis://redis:6379/0"), decode_responses=True)
            r.sadd("active_symbols", symbol)
            await self.send(json.dumps({"type":"subscribed","symbol":symbol}))
        elif action == "unsubscribe":
            symbol = data.get("symbol")
            if not symbol:
                return
            await self.channel_layer.group_discard(f"symbol_{symbol}", self.channel_name)
            if symbol in self.subscriptions:
                self.subscriptions.remove(symbol)
            await self.send(json.dumps({"type":"unsubscribed","symbol":symbol}))

    async def market_tick(self, event):
        tick = event.get("tick")
        await self.send(json.dumps({"type":"tick","data": tick}))

    async def user_message(self, event):
        """
        Send private messages like order_update / position_update / account_update
        event contains 'payload' dict
        """
        payload = event.get("payload")
        await self.send(json.dumps(payload))
