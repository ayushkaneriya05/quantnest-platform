# backend/marketdata/management/commands/run_marketdata_gateway.py
from django.core.management.base import BaseCommand
from marketdata.fyers_ws_client import run_fyers_ws, run_forever_from_env
import threading

class Command(BaseCommand):
    help = "Run marketdata gateway: fyers/apiv3 ws client + redis forwarder (if configured)"

    def add_arguments(self, parser):
        parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols to subscribe (e.g. RELIANCE,TCS)")

    def handle(self, *args, **options):
        syms = options.get("symbols")
        if syms:
            subs = [s.strip().upper() for s in syms.split(",") if s.strip()]
        else:
            subs = None
        # run WS (blocking)
        if subs:
            run_fyers_ws(subscribe_symbols=subs)
        else:
            run_forever_from_env()