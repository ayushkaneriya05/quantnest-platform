"""Offline, one-shot local observation-buffer maintenance."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Resize one local market buffer with all runtime owners stopped. History reloads on feed startup."

    def add_arguments(self, parser):
        parser.add_argument("symbol")
        parser.add_argument("--capacity", type=int, required=True)
        parser.add_argument("--timeframe", choices=("1m", "1D"), default="1m")

    def handle(self, *args, **options):
        from execution.launcher import execution_ownership
        from common.redis import runtime_redis
        from marketdata.contracts import normalize_symbol
        from instruments.models import Instrument
        from marketdata.shared_memory import SharedMemoryManager
        if any(runtime_redis().scan_iter(match="quantnest:lease:*", count=100)):
            raise CommandError("Stop runtime services and allow leases to expire before resizing buffers.")
        if options["capacity"] < 2:
            raise CommandError("Capacity must be at least two candles.")
        symbol = normalize_symbol(options["symbol"])
        timeframe = options["timeframe"]
        if not Instrument.objects.filter(sym_ticker=symbol).exists():
            raise CommandError("Unknown canonical instrument symbol.")
        # Hold the execution lock throughout maintenance, not just while checking
        # it. A new worker group must not open this buffer during replacement.
        try:
            with execution_ownership():
                try:
                    previous = SharedMemoryManager(symbol, timeframe)
                except FileNotFoundError:
                    previous = None
                if previous:
                    previous.unlink()
                replacement = SharedMemoryManager(symbol, timeframe, create=True, max_size=options["capacity"])
                replacement.close()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Buffer resized for {symbol}; restart market-data before execution."))
