import signal
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
        client.start_subscription_sync()
        self.stdout.write(self.style.SUCCESS("Fyers websocket connected. Sync loop running."))

        shutdown_requested = False

        def _shutdown(signum, frame):
            nonlocal shutdown_requested
            shutdown_requested = True
            self.stdout.write(self.style.WARNING(f"Shutdown signal {signum} received. Stopping..."))

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            while not shutdown_requested:
                time.sleep(1)
        finally:
            self.stdout.write(self.style.WARNING("Shutting down Fyers ingestion worker..."))
            client.shutdown()
            self.stdout.write(self.style.SUCCESS("Shutdown complete."))
