# backend/marketdata/management/commands/backfill_ohlc.py
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from ohlc.backfill import fetch_historical

class Command(BaseCommand):
    help = "Backfills historical OHLC data for Nifty 500 stocks."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days to backfill data for. Default is 365.',
        )
        parser.add_argument(
            '--symbols-file',
            type=str,
            default='backend/data/nifty500_symbols.json',
            help='Path to the JSON file containing the list of symbols.'
        )

    def handle(self, *args, **options):
        days_to_backfill = options['days']
        symbols_file_path = options['symbols_file']
        
        try:
            with open(symbols_file_path, 'r') as f:
                symbols = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Symbols file not found at: {symbols_file_path}"))
            return

        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days_to_backfill)

        self.stdout.write(self.style.SUCCESS(
            f"Starting backfill for {len(symbols)} symbols from {from_date} to {to_date}."
        ))

        for symbol in symbols:
            self.stdout.write(f"Fetching data for {symbol}...")
            try:
                # Assuming 1-minute resolution for backfill
                candles = fetch_historical(
                    symbol=f"NSE:{symbol}-EQ",
                    from_date=from_date,
                    to_date=to_date,
                    resolution_minutes=1,
                    save_to_db=True
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully fetched and stored {len(candles)} candles for {symbol}."
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to fetch data for {symbol}: {e}"
                ))

        self.stdout.write(self.style.SUCCESS("Historical data backfill complete."))