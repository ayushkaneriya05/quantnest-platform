"""Offline, one-shot local observation-buffer maintenance."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Resize one local market buffer with all runtime owners stopped. History reloads on feed startup."

    def add_arguments(self, parser):
        parser.add_argument("symbol")
        parser.add_argument("--capacity", type=int, required=True)

    def handle(self, *args, **options):
        from core.redis import runtime_redis
        from marketdata.services import MarketDataService
        from marketdata.shared_memory import SharedMemoryManager
        if any(runtime_redis().scan_iter(match="quantnest:lease:*", count=100)):
            raise CommandError("Stop runtime services and allow leases to expire before resizing buffers.")
        if options["capacity"] < 2:
            raise CommandError("Capacity must be at least two candles.")
        symbol = MarketDataService.normalize_symbol(options["symbol"])
        if MarketDataService.get_instrument(symbol) is None:
            raise CommandError("Unknown canonical instrument symbol.")
        try:
            previous = SharedMemoryManager(symbol, "1m")
        except FileNotFoundError:
            previous = None
        if previous:
            previous.unlink()
        replacement = SharedMemoryManager(symbol, "1m", create=True, max_size=options["capacity"])
        replacement.close()
        self.stdout.write(self.style.SUCCESS(f"Buffer resized for {symbol}; restart market-data before execution."))
