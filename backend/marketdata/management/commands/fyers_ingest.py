import time

from django.core.management.base import BaseCommand

from marketdata.live_feed import FyersLiveFeedClient, LiveMarketDataRegistry


class Command(BaseCommand):
    help = "Starts the Fyers websocket ingestion worker and syncs subscriptions from active paper accounts."

    def handle(self, *args, **options):
        symbols = LiveMarketDataRegistry.refresh_from_active_accounts()
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting live market ingestion with {len(symbols)} tracked symbol(s)."
            )
        )

        client = FyersLiveFeedClient()
        client.connect()
        self.stdout.write(self.style.SUCCESS("Fyers websocket connected. Sync loop running."))

        while True:
            client.sync_subscriptions()
            time.sleep(15)
