"""Sync the configured provider's instrument master into QuantNest."""
import logging
import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from instruments.models import Instrument
from marketdata.providers import provider

logger = logging.getLogger(__name__)

SYNC_FIELDS = [
    'fy_token', 'exchange_token', 'symbol', 'name', 'short_name', 'display_name',
    'description', 'isin', 'exchange', 'segment', 'series', 'ex_inst_type',
    'instrument_type', 'option_type', 'currency_code', 'strike_price', 'expiry_date',
    'underlying_symbol', 'underlying_fy_token', 'lot_size', 'tick_size', 'qty_freeze',
    'qty_multiplier', 'face_value', 'circuit_limit_upper', 'circuit_limit_lower',
    'trading_session', 'previous_close', 'previous_oi', 'is_mtf_tradable', 'mtf_margin',
    'asm_gsm_flag', 'has_options', 'has_futures', 'stream', 'is_tradeable', 'is_active',
    'last_sync_date',
]


class Command(BaseCommand):
    help = "Sync instruments from the configured market-data provider"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            action="append",
            choices=list(provider().instrument_master().SOURCES),
            help="Specific source(s) to sync. Omit to sync all.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to database.",
        )
        parser.add_argument(
            "--archive-stale",
            action="store_true",
            help="Deactivate instruments missing from the provider master and retain their historical data.",
        )

    def handle(self, *args, **options):
        self.master = provider().instrument_master()
        sources = options["source"] or list(self.master.SOURCES)
        dry_run = options["dry_run"]
        archive_stale = options["archive_stale"]
        total_created = 0
        total_updated = 0
        total_deactivated = 0
        total_errors = 0

        # Prefetch ALL existing instruments once for the entire run.
        # This avoids re-querying 200K+ rows before every source file.
        t0 = time.monotonic()
        existing_qs = Instrument.objects.values_list('id', 'sym_ticker', 'fy_token')
        existing_by_ticker = {}
        existing_by_token = {}
        for row_id, sym_ticker, fy_token in existing_qs.iterator(chunk_size=10000):
            rec = {'id': row_id, 'sym_ticker': sym_ticker, 'fy_token': fy_token}
            existing_by_ticker[sym_ticker] = rec
            existing_by_token[fy_token] = rec
        self.stdout.write(f"  Prefetched {len(existing_by_ticker)} existing instruments in {time.monotonic() - t0:.1f}s")

        for source_key in sources:
            url = self.master.SOURCES[source_key]
            self.stdout.write(f"\nSyncing {source_key} from {url}")

            try:
                data = self.master.download(source_key)
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to download {source_key}: {exc}"))
                total_errors += 1
                continue
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to parse JSON for {source_key}: {exc}"))
                total_errors += 1
                continue

            if not data:
                self.stderr.write(self.style.ERROR(f"  Empty instrument master for {source_key}."))
                total_errors += 1
                continue
            self.stdout.write(f"  Downloaded {len(data)} entries")

            t1 = time.monotonic()
            created, updated, errors, synced_tickers = self._sync_source(
                data, dry_run, existing_by_ticker, existing_by_token,
            )
            self.stdout.write(f"  Synced in {time.monotonic() - t1:.1f}s")

            deactivated = 0
            if archive_stale and not dry_run and not errors and synced_tickers and source_key in self.master.SOURCE_FILTERS:
                t2 = time.monotonic()
                deactivated = self._archive_stale_source(source_key, synced_tickers)
                self.stdout.write(f"  Stale cleanup in {time.monotonic() - t2:.1f}s")

            prefix = "[DRY RUN] " if dry_run else ""
            self.stdout.write(self.style.SUCCESS(
                f"  {prefix}{source_key}: {created} created, {updated} updated, "
                f"{deactivated} deactivated, {errors} errors"
            ))

            total_created += created
            total_updated += updated
            total_deactivated += deactivated
            total_errors += errors

        summary = (
            f"Sync complete: {total_created} created, {total_updated} updated, "
            f"{total_deactivated} deactivated, {total_errors} errors"
        )
        if total_errors:
            raise CommandError(summary + ". Failed sources were not archived.")
        self.stdout.write(self.style.SUCCESS(summary))

    def _sync_source(self, data, dry_run, existing_by_ticker, existing_by_token):
        created = 0
        updated = 0
        errors = 0
        synced_tickers = set()

        stale_updates = []
        all_instruments = []  # Single list for upsert

        for sym_ticker, entry in data.items():
            try:
                mapped = self.master.map_entry(sym_ticker, entry)
                fy_token = mapped.pop("fy_token")
                if not fy_token:
                    errors += 1
                    continue

                mapped["fy_token"] = fy_token
                mapped.pop("sym_ticker", None)
                synced_tickers.add(sym_ticker)

                # Handle fy_token recycled by the exchange to a different sym_ticker
                existing_token_row = existing_by_token.get(fy_token)
                if existing_token_row and existing_token_row['sym_ticker'] != sym_ticker:
                    stale_id = existing_token_row['id']
                    new_stale_token = f"STALE_{stale_id}_{fy_token}"[:30]
                    stale_inst = Instrument(id=stale_id, fy_token=new_stale_token, is_active=False)
                    stale_updates.append(stale_inst)

                    # Update memory maps so subsequent iterations don't collide
                    del existing_by_token[fy_token]
                    existing_token_row['fy_token'] = new_stale_token
                    existing_by_token[new_stale_token] = existing_token_row

                # Count creates vs updates for reporting
                existing_ticker_row = existing_by_ticker.get(sym_ticker)
                if existing_ticker_row:
                    updated += 1
                else:
                    created += 1

                if dry_run:
                    continue

                # Build a single Instrument object — bulk_create with update_conflicts
                # handles both INSERT (new) and UPDATE (existing) in one SQL statement.
                inst = Instrument(sym_ticker=sym_ticker, **mapped)
                all_instruments.append(inst)

                # Track new entries in memory maps
                if not existing_ticker_row:
                    new_rec = {'id': None, 'sym_ticker': sym_ticker, 'fy_token': fy_token}
                    existing_by_ticker[sym_ticker] = new_rec
                    existing_by_token[fy_token] = new_rec

            except Exception as exc:
                errors += 1
                if errors <= 10:
                    logger.warning("  Error processing %s: %s", sym_ticker, exc)

        if not dry_run:
            try:
                with transaction.atomic():
                    # Step 1: Free up recycled fy_tokens (tiny list, usually 0)
                    if stale_updates:
                        Instrument.objects.bulk_update(stale_updates, ['fy_token', 'is_active'], batch_size=2000)

                    # Step 2: Upsert all instruments in one shot.
                    # This generates: INSERT INTO ... ON CONFLICT (sym_ticker) DO UPDATE SET ...
                    # which is a SINGLE SQL statement per batch instead of one per row.
                    if all_instruments:
                        Instrument.objects.bulk_create(
                            all_instruments,
                            update_conflicts=True,
                            unique_fields=['sym_ticker'],
                            update_fields=SYNC_FIELDS,
                            batch_size=2000,
                        )

            except Exception as exc:
                logger.error("Bulk database operation failed: %s", exc)
                errors += created + updated
                created = 0
                updated = 0

        return created, updated, errors, synced_tickers

    def _archive_stale_source(self, source_key, synced_tickers):
        """Archive missing contracts without deleting their identities or candles."""
        qs = Instrument.objects.filter(**self.master.SOURCE_FILTERS[source_key], is_active=True)
        ids = [pk for pk, ticker in qs.values_list('pk', 'sym_ticker') if ticker not in synced_tickers]
        count = 0
        for start in range(0, len(ids), 2000):
            count += Instrument.objects.filter(pk__in=ids[start:start + 2000]).update(is_active=False)
        return count
