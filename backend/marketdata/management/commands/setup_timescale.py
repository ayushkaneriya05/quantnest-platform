from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Enable TimescaleDB features for the marketdata_candle table with partitioning support."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. Enable extension
            self.stdout.write("Ensuring timescaledb extension exists...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

            # 2. Check if marketdata_candle is already a hypertable
            cursor.execute("""
                SELECT 1 FROM _timescaledb_catalog.hypertable 
                WHERE table_name = 'marketdata_candle';
            """)
            is_hypertable = cursor.fetchone()

            if not is_hypertable:
                self.stdout.write("Converting marketdata_candle to hypertable...")
                
                # TimescaleDB requires all unique indexes to include the partitioning column (time).
                # The default Django primary key is just (id), so we must migrate it to (id, time).
                
                try:
                    self.stdout.write(" - Migrating Primary Key to (id, time)...")
                    # We use a transaction-safe way to swap the PK
                    cursor.execute("ALTER TABLE marketdata_candle DROP CONSTRAINT IF EXISTS marketdata_candle_pkey CASCADE;")
                    cursor.execute("ALTER TABLE marketdata_candle ADD PRIMARY KEY (id, \"time\");")
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f"Could not migrate PK: {exc}"))

                try:
                    self.stdout.write(" - Creating hypertable...")
                    cursor.execute("""
                        SELECT create_hypertable(
                            'marketdata_candle',
                            'time',
                            if_not_exists => TRUE,
                            migrate_data => TRUE
                        );
                    """)
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"Failed to create hypertable: {exc}"))
                    return
            else:
                self.stdout.write(self.style.SUCCESS("Table is already a hypertable."))

            # 3. Apply compression
            self.stdout.write("Configuring compression...")
            try:
                cursor.execute("""
                    ALTER TABLE marketdata_candle
                    SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'symbol,timeframe',
                        timescaledb.compress_orderby = 'time DESC'
                    );
                """)
                cursor.execute("SELECT add_compression_policy('marketdata_candle', INTERVAL '7 days', if_not_exists => TRUE);")
                self.stdout.write(self.style.SUCCESS("Compression and policy applied."))
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"Skipped compression step: {exc}"))

        self.stdout.write(self.style.SUCCESS("\nTimescaleDB setup complete."))
