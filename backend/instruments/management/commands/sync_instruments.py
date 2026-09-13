"""
Management command to sync instrument master data from Fyers public JSON files.

Usage:
    py manage.py sync_instruments
    py manage.py sync_instruments --source NSE_CM
    py manage.py sync_instruments --delete-stale
"""
import logging
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from instruments.models import Instrument

logger = logging.getLogger(__name__)

SOURCES = {
    "NSE_CM": "https://public.fyers.in/sym_details/NSE_CM_sym_master.json",
    "NSE_FO": "https://public.fyers.in/sym_details/NSE_FO_sym_master.json",
    "NSE_CD": "https://public.fyers.in/sym_details/NSE_CD_sym_master.json",
    "NSE_COM": "https://public.fyers.in/sym_details/NSE_COM_sym_master.json",
    "BSE_CM": "https://public.fyers.in/sym_details/BSE_CM_sym_master.json",
    "BSE_FO": "https://public.fyers.in/sym_details/BSE_FO_sym_master.json",
    "MCX_COM": "https://public.fyers.in/sym_details/MCX_COM_sym_master.json",
}

SOURCE_FILTERS = {
    "NSE_CM": {"exchange": "NSE", "segment": 10},
    "NSE_FO": {"exchange": "NSE", "segment": 11},
    "NSE_CD": {"exchange": "NSE", "segment": 12},
    "NSE_COM": {"exchange": "NSE", "segment": 20},
    "BSE_CM": {"exchange": "BSE", "segment": 10},
    "BSE_FO": {"exchange": "BSE", "segment": 11},
    "MCX_COM": {"exchange": "MCX", "segment": 20},
}

EXCHANGE_MAP = {10: "NSE", 11: "MCX", 12: "BSE"}

INST_TYPE_MAP = {
    0: "STOCK",
    1: "STOCK",
    2: "BOND",
    3: "STOCK",
    4: "STOCK",
    5: "BOND",
    6: "BOND",
    7: "BOND",
    8: "MF",
    9: "ETF",
    10: "INDEX",
    50: "STOCK",
    11: "FUTURE",
    12: "FUTURE",
    13: "FUTURE",
    14: "OPTION",
    15: "OPTION",
    16: "CURRENCY",
    17: "CURRENCY",
    18: "CURRENCY",
    19: "CURRENCY",
    20: "CURRENCY",
    21: "CURRENCY",
    22: "CURRENCY",
    23: "CURRENCY",
    24: "CURRENCY",
    25: "CURRENCY",
    30: "COMMODITY",
    31: "COMMODITY",
    32: "COMMODITY",
    33: "COMMODITY",
    34: "COMMODITY",
    35: "COMMODITY",
    36: "COMMODITY",
    37: "COMMODITY",
}

# All data fields that map_entry produces (excluding sym_ticker which is the lookup key)
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


def _safe_decimal(value, default=None):
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _safe_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_expiry(expiry_str):
    if not expiry_str:
        return None
    try:
        timestamp = int(expiry_str)
        if timestamp > 0:
            return datetime.fromtimestamp(timestamp).date()
    except (ValueError, TypeError, OSError):
        pass
    try:
        return datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_last_update(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def map_entry(sym_ticker, data):
    ex_inst_type = _safe_int(data.get("exInstType"), 0)
    instrument_type = INST_TYPE_MAP.get(ex_inst_type, "STOCK")
    exchange_code = data.get("exchange", 10)
    exchange = EXCHANGE_MAP.get(exchange_code, "NSE")

    strike = _safe_decimal(data.get("strikePrice"))
    if strike is not None and strike < 0:
        strike = None

    return {
        "fy_token": data.get("fyToken", ""),
        "exchange_token": _safe_int(data.get("exToken"), 0),
        "symbol": data.get("exSymbol", ""),
        "name": (data.get("exSymName") or data.get("symDetails") or "")[:255],
        "sym_ticker": sym_ticker,
        "short_name": (data.get("short_name") or "")[:50],
        "display_name": (data.get("display_format_mob") or "")[:100],
        "description": (data.get("symbolDesc") or data.get("symDetails") or "")[:255],
        "isin": (data.get("isin") or "")[:20],
        "exchange": exchange,
        "segment": data.get("segment", 10),
        "series": (data.get("exSeries") or "")[:10],
        "ex_inst_type": ex_inst_type,
        "instrument_type": instrument_type,
        "option_type": (data.get("optType") or "XX")[:5],
        "currency_code": (data.get("currencyCode") or "INR")[:5],
        "strike_price": strike,
        "expiry_date": _parse_expiry(data.get("expiryDate")),
        "underlying_symbol": (data.get("underSym") or "")[:50],
        "underlying_fy_token": (data.get("underFyTok") or "")[:30],
        "lot_size": _safe_int(data.get("minLotSize"), 1),
        "tick_size": _safe_decimal(data.get("tickSize"), Decimal("0.05")),
        "qty_freeze": _safe_int(data.get("qtyFreeze")),
        "qty_multiplier": _safe_decimal(data.get("qtyMultiplier"), Decimal("1.0")),
        "face_value": _safe_decimal(data.get("faceValue")),
        "circuit_limit_upper": _safe_decimal(data.get("upperPrice")),
        "circuit_limit_lower": _safe_decimal(data.get("lowerPrice")),
        "trading_session": (data.get("tradingSession") or "")[:100],
        "previous_close": _safe_decimal(data.get("previousClose")),
        "previous_oi": _safe_decimal(data.get("previousOi")),
        "is_mtf_tradable": bool(data.get("is_mtf_tradable", 0)),
        "mtf_margin": _safe_decimal(data.get("mtf_margin")),
        "asm_gsm_flag": (data.get("asmGsmVal") or "")[:100],
        "has_options": bool(data.get("has_options", False)),
        "has_futures": bool(data.get("has_futures", False)),
        "stream": (data.get("stream") or "")[:20],
        "is_tradeable": bool(data.get("tradeStatus", 1)),
        "is_active": True,
        "last_sync_date": _parse_last_update(data.get("lastUpdate")),
    }


class Command(BaseCommand):
    help = "Sync instrument master data from Fyers public JSON files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            action="append",
            choices=list(SOURCES.keys()),
            help="Specific source(s) to sync. Omit to sync all.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to database.",
        )
        parser.add_argument(
            "--delete-stale",
            action="store_true",
            help="Delete instruments missing from Fyers master. Referenced stale rows are deactivated.",
        )

    def handle(self, *args, **options):
        sources = options["source"] or list(SOURCES.keys())
        dry_run = options["dry_run"]
        delete_stale = options["delete_stale"]
        total_created = 0
        total_updated = 0
        total_deleted = 0
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
            url = SOURCES[source_key]
            self.stdout.write(f"\nSyncing {source_key} from {url}")

            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to download {source_key}: {exc}"))
                total_errors += 1
                continue
            except ValueError as exc:
                self.stderr.write(self.style.ERROR(f"  Failed to parse JSON for {source_key}: {exc}"))
                total_errors += 1
                continue

            self.stdout.write(f"  Downloaded {len(data)} entries")

            t1 = time.monotonic()
            created, updated, errors, synced_tokens = self._sync_source(
                data, dry_run, existing_by_ticker, existing_by_token,
            )
            self.stdout.write(f"  Synced in {time.monotonic() - t1:.1f}s")

            deleted = 0
            deactivated = 0
            if delete_stale and not dry_run and synced_tokens and source_key in SOURCE_FILTERS:
                t2 = time.monotonic()
                deleted, deactivated = self._cleanup_stale_source(
                    source_key, synced_tokens, existing_by_ticker, existing_by_token,
                )
                self.stdout.write(f"  Stale cleanup in {time.monotonic() - t2:.1f}s")

            prefix = "[DRY RUN] " if dry_run else ""
            self.stdout.write(self.style.SUCCESS(
                f"  {prefix}{source_key}: {created} created, {updated} updated, "
                f"{deleted} deleted, {deactivated} deactivated, {errors} errors"
            ))

            total_created += created
            total_updated += updated
            total_deleted += deleted
            total_deactivated += deactivated
            total_errors += errors

        self.stdout.write(self.style.SUCCESS(
            f"\nSync complete: {total_created} created, {total_updated} updated, "
            f"{total_deleted} deleted, {total_deactivated} deactivated, {total_errors} errors"
        ))

    def _sync_source(self, data, dry_run, existing_by_ticker, existing_by_token):
        created = 0
        updated = 0
        errors = 0
        synced_tokens = set()

        stale_updates = []
        all_instruments = []  # Single list for upsert

        for sym_ticker, entry in data.items():
            try:
                mapped = map_entry(sym_ticker, entry)
                fy_token = mapped.pop("fy_token")
                if not fy_token:
                    errors += 1
                    continue

                mapped["fy_token"] = fy_token
                mapped.pop("sym_ticker", None)
                synced_tokens.add(fy_token)

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

        return created, updated, errors, synced_tokens

    def _cleanup_stale_source(self, source_key, synced_tokens, existing_by_ticker, existing_by_token):
        """
        Delete/deactivate instruments that are no longer in the Fyers master JSON.

        Performance strategy:
        - Stale set computed via Python set subtraction (no SQL NOT IN).
        - Business reference check via bulk WHERE IN queries.
        - Unreferenced instruments deleted via raw SQL in small committed chunks
          to bypass Django's O(N) cascade collector and prevent massive table locks.
        """
        source_filter = SOURCE_FILTERS[source_key]

        # Fetch (id, fy_token) for this source segment — fast with (exchange, segment) index
        source_instruments = (
            Instrument.objects
            .filter(**source_filter, is_active=True)
            .values_list('id', 'fy_token')
        )

        source_token_to_id = {}
        for inst_id, fy_token in source_instruments.iterator(chunk_size=10000):
            source_token_to_id[fy_token] = inst_id

        # Stale = in DB but NOT in downloaded JSON
        stale_tokens = set(source_token_to_id.keys()) - synced_tokens
        if not stale_tokens:
            return 0, 0

        stale_ids = [source_token_to_id[token] for token in stale_tokens]
        self.stdout.write(f"    Found {len(stale_ids)} stale instruments to process")

        # Determine which stale instruments have business references (skip Candle & MarketEvent)
        SKIP_LABELS = {"marketdata.Candle", "marketdata.MarketEvent"}
        referenced_ids = set()
        
        self.stdout.write("    Checking business references...")
        t_ref_start = time.monotonic()
        for relation in Instrument._meta.related_objects:
            if relation.related_model._meta.label in SKIP_LABELS:
                continue

            field_name = getattr(relation.field, 'name', None)
            if not field_name:
                continue

            try:
                for i in range(0, len(stale_ids), 2000):
                    chunk = stale_ids[i:i + 2000]
                    refs = (
                        relation.related_model.objects
                        .filter(**{f"{field_name}__in": chunk})
                        .values_list(field_name, flat=True)
                        .distinct()
                    )
                    referenced_ids.update(refs)
            except Exception as exc:
                logger.debug("Could not inspect relation %s: %s", field_name, exc)
                referenced_ids.update(stale_ids)
        
        self.stdout.write(f"    Reference check complete in {time.monotonic() - t_ref_start:.1f}s")

        delete_ids = list(set(stale_ids) - referenced_ids)
        deactivate_ids = list(referenced_ids & set(stale_ids))

        deleted = 0
        deactivated = 0

        # Bulk delete unreferenced instruments in chunks
        if delete_ids:
            from django.db import connection

            candle_table = "marketdata_candle"
            event_table = "marketdata_marketevent"
            instrument_table = Instrument._meta.db_table

            self.stdout.write(f"    Deleting {len(delete_ids)} unreferenced instruments...")
            t_del_start = time.monotonic()
            
            # Process in small chunks, committing each one to avoid giant locks
            for i in range(0, len(delete_ids), 2000):
                chunk = delete_ids[i:i + 2000]
                
                try:
                    cursor = connection.cursor()
                   
                    cursor.execute("SET session_replication_role = 'replica';")
                    try:
                        with transaction.atomic():
                            cursor.execute(f"DELETE FROM {candle_table} WHERE instrument_id = ANY(%s)", [chunk])
                            cursor.execute(f"DELETE FROM {event_table} WHERE instrument_id = ANY(%s)", [chunk])
                            cursor.execute(f"DELETE FROM {instrument_table} WHERE id = ANY(%s)", [chunk])
                    finally:
                        cursor.execute("SET session_replication_role = 'origin';")
                        
                    deleted += len(chunk)
                except Exception as exc:
                    logger.error("Failed to raw delete chunk of stale instruments: %s", exc)
                    # Fallback to deactivate if strict foreign key constraint fails
                    deactivate_ids.extend(chunk)

            self.stdout.write(f"    Deletion complete in {time.monotonic() - t_del_start:.1f}s")

            # Update memory maps
            id_to_token = {source_token_to_id[token]: token for token in stale_tokens}
            for inst_id in delete_ids:
                token = id_to_token.get(inst_id)
                if token:
                    rec = existing_by_token.pop(token, None)
                    if rec:
                        existing_by_ticker.pop(rec['sym_ticker'], None)

        # Bulk deactivate referenced instruments (or ones that failed raw deletion)
        if deactivate_ids:
            for i in range(0, len(deactivate_ids), 2000):
                chunk = deactivate_ids[i:i + 2000]
                with transaction.atomic():
                    deactivated += Instrument.objects.filter(id__in=chunk).update(is_active=False)

        return deleted, deactivated
