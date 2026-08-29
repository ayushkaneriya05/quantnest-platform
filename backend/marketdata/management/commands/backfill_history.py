from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from instruments.models import Instrument

from marketdata.services import MarketDataService


class Command(BaseCommand):
    help = "Backfill Timescale/PostgreSQL candle history from Fyers in 90-day chunks."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365)
        parser.add_argument("--timeframe", type=str, default="1m")
        parser.add_argument("--symbols", nargs="+")

    def handle(self, *args, **options):
        symbols = options["symbols"]
        days = int(options["days"])

        if not symbols:
            symbols = list(
                Instrument.objects.filter(is_tradeable=True, is_active=True)
                .exclude(sym_ticker="")
                .values_list("sym_ticker", flat=True)[:100]
            )

        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        end_date = datetime.now(timezone.utc).date()
        self.stdout.write(self.style.SUCCESS(f"Backfilling {len(symbols)} symbols to Timescale/PostgreSQL"))

        for symbol in symbols:
            chunk_start = start_date
            while chunk_start <= end_date:
                chunk_end = min(chunk_start + timedelta(days=90), end_date)
                candles = MarketDataService.backfill_candles_from_broker(
                    symbol=symbol,
                    date_from=chunk_start.isoformat(),
                    date_to=chunk_end.isoformat(),
                    timeframe=options["timeframe"],
                )
                self.stdout.write(
                    f"{symbol} {chunk_start.isoformat()} -> {chunk_end.isoformat()}: stored {len(candles)} candles"
                )
                chunk_start = chunk_end + timedelta(days=1)
