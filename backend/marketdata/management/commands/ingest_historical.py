from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from instruments.models import Instrument
from marketdata.services import MarketDataService

class Command(BaseCommand):
    help = 'Ingest historical candle data from Fyers into Timescale/PostgreSQL (uses 90-day chunks per broker limit)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to ingest (e.g. NSE:SBIN-EQ). Omit to ingest from instruments.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back from today.',
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Start date (YYYY-MM-DD). Supersedes --days.',
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--timeframe',
            type=str,
            default='1m',
            help='Timeframe to fetch (e.g., 1m, 1D). Defaults to 1m.',
        )

    def handle(self, *args, **options):
        symbols = options['symbols']
        days = options['days']
        start_str = options['start']
        end_str = options['end']
        timeframe = options['timeframe']

        if start_str:
            date_from = start_str
        else:
            date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        if end_str:
            date_to = end_str
        else:
            date_to = datetime.now().strftime('%Y-%m-%d')

        # If no symbols provided, get from all active instruments or watchlist
        # For professional level, let's fetch from all tradeable instruments for now or a subset
        if not symbols:
            self.stdout.write("No symbols provided. Fetching from tradeable instruments...")
            instruments = Instrument.objects.filter(is_tradeable=True, is_active=True)[:50] # Limit for now
            symbols = [inst.sym_ticker for inst in instruments]

        self.stdout.write(f"Starting {timeframe} ingestion for {len(symbols)} symbols from {date_from} to {date_to}")
        self.stdout.write("Using 90-day chunks (broker API limit)")

        total_upserted = 0
        for symbol in symbols:
            self.stdout.write(f"  Processing {symbol}...")
            
            # Convert to datetime objects for chunking
            chunk_start = datetime.strptime(date_from, '%Y-%m-%d').date()
            chunk_end = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            symbol_upserted = 0
            while chunk_start <= chunk_end:
                # 90-day chunk (broker API limit)
                current_chunk_end = min(chunk_start + timedelta(days=90), chunk_end)
                
                candles = MarketDataService.backfill_candles_from_broker(
                    symbol, 
                    chunk_start.isoformat(), 
                    current_chunk_end.isoformat(), 
                    timeframe=timeframe
                )
                
                if candles:
                    count = len(candles)
                    symbol_upserted += count
                    total_upserted += count
                    self.stdout.write(self.style.SUCCESS(
                        f"    {symbol} {chunk_start.isoformat()} -> {current_chunk_end.isoformat()}: {count} candles"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"    {symbol} {chunk_start.isoformat()} -> {current_chunk_end.isoformat()}: No data"
                    ))
                
                chunk_start = current_chunk_end + timedelta(days=1)
            
            self.stdout.write(self.style.SUCCESS(f"  ✓ {symbol} total: {symbol_upserted} candles"))

        self.stdout.write(self.style.SUCCESS(f"\n✓ Ingestion complete. Total records updated/inserted: {total_upserted}"))
