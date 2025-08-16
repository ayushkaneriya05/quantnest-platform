# backend/marketdata/management/commands/run_marketdata_gateway.py
import asyncio
import threading
from django.core.management.base import BaseCommand
from marketdata.fyers_ws_client import run_fyers_ws_stub
from marketdata.redis_forwarder import run_forwarder

class Command(BaseCommand):
    help = "Run marketdata gateway: fyers ws client + redis forwarder"

    def handle(self, *args, **options):
        # run redis forwarder in a thread (blocking)
        t = threading.Thread(target=run_forwarder, daemon=True)
        t.start()
        # run fyers ws client in asyncio loop (blocking)
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run_fyers_ws_stub())
        except KeyboardInterrupt:
            pass
