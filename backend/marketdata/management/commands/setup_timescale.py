"""Configure candle storage atomically during an operator maintenance window."""
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction


class Command(BaseCommand):
    help = "Convert candles to a Timescale hypertable and configure compression."

    def handle(self, *args, **options):
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
                cursor.execute(
                    "SELECT 1 FROM _timescaledb_catalog.hypertable "
                    "WHERE schema_name = 'public' AND table_name = 'marketdata_candle'"
                )
                if not cursor.fetchone():
                    # Every unique index must include the partition time. Do not
                    # CASCADE away dependencies; an incompatible schema must fail.
                    cursor.execute("ALTER TABLE marketdata_candle DROP CONSTRAINT IF EXISTS marketdata_candle_pkey")
                    cursor.execute('ALTER TABLE marketdata_candle ADD PRIMARY KEY (id, "time")')
                    cursor.execute(
                        "SELECT create_hypertable('marketdata_candle', 'time', "
                        "if_not_exists => TRUE, migrate_data => TRUE)"
                    )
                cursor.execute(
                    "ALTER TABLE marketdata_candle SET (timescaledb.compress, "
                    "timescaledb.compress_segmentby = 'symbol,timeframe', "
                    "timescaledb.compress_orderby = 'time DESC')"
                )
                cursor.execute(
                    "SELECT add_compression_policy('marketdata_candle', INTERVAL '7 days', if_not_exists => TRUE)"
                )
        except DatabaseError as error:
            raise CommandError("Timescale setup failed and was rolled back. Review database permissions/schema and the reported cause.") from error
        self.stdout.write(self.style.SUCCESS("Candle hypertable and compression configured."))
