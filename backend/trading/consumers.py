# backend/trading/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
from django.conf import settings

class OrderbookConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = self.scope['url_route']['kwargs']['symbol']
        self.group_name = f'orderbook_{self.symbol}'

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # Send initial orderbook state
        await self.send_orderbook_snapshot()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_orderbook_snapshot(self):
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        bids = await r.zrange(f"orderbook:bids:{self.symbol}", 0, 9, withscores=True, desc=True)
        asks = await r.zrange(f"orderbook:asks:{self.symbol}", 0, 9, withscores=True)
        
        book = {
            'bids': [{'price': score, 'qty': json.loads(member)['qty']} for member, score in bids],
            'asks': [{'price': score, 'qty': json.loads(member)['qty']} for member, score in asks]
        }
        await self.send(text_data=json.dumps({
            'type': 'orderbook_snapshot',
            'data': book
        }))

    async def orderbook_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'orderbook_update',
            'data': event['data']
        }))