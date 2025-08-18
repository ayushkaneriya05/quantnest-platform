# backend/marketdata/management/commands/broadcast_delayed_ticks.py
import json
import time
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from marketdata.models import LiveTick

DELAY_MINUTES = 15

class Command(BaseCommand):
    help = "Broadcasts LiveTick entries after a 15-minute delay to WebSocket subscribers (no Redis/Celery)."

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()

        while True:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=DELAY_MINUTES)
            to_send = list(LiveTick.objects.filter(timestamp__lte=cutoff)[:500])
            for tick in to_send:
                # Broadcast to symbol-specific and global groups
                payload = {'symbol': tick.symbol, 'tick': tick.payload, 'timestamp': tick.timestamp.isoformat()}
                try:
                    async_to_sync(channel_layer.group_send)(f'market_{tick.symbol}', {
                        'type': 'market_data_message',
                        'message': payload
                    })
                    async_to_sync(channel_layer.group_send)('marketdata', {
                        'type': 'market_data_message',
                        'message': payload
                    })
                except Exception:
                    pass
                # Delete after broadcasting to avoid re-sending; alternatively add a 'sent_at' flag
                tick.delete()
            time.sleep(1)
