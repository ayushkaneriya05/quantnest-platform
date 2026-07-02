"""
Management command to sync instrument master data from Fyers public JSON files.

Usage:
    py manage.py sync_instruments
    py manage.py sync_instruments --source NSE_CM
    py manage.py sync_instruments --delete-stale
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError

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


def _has_business_references(instrument):
    for relation in instrument._meta.related_objects:
        if relation.related_model._meta.label == "marketdata.Candle":
            continue
        accessor = relation.get_accessor_name()
        if not accessor:
            continue
        try:
            related = getattr(instrument, accessor)
            if hasattr(related, "exists") and related.exists():
                return True
            if hasattr(related, "all") and related.all().exists():
                return True
        except relation.related_model.DoesNotExist:
            continue
        except Exception:
            logger.debug("Could not inspect relation %s for %s", accessor, instrument)
            return True
    return False


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
            created, updated, errors, synced_tokens = self._sync_source(data, dry_run)

            deleted = 0
            deactivated = 0
            if delete_stale and not dry_run and synced_tokens and source_key in SOURCE_FILTERS:
                deleted, deactivated = self._cleanup_stale_source(source_key, synced_tokens)

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

    def _sync_source(self, data, dry_run):
        created = 0
        updated = 0
        errors = 0
        synced_tokens = set()

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
                if dry_run:
                    created += 1
                    continue

                try:
                    _, was_created = Instrument.objects.update_or_create(
                        sym_ticker=sym_ticker,
                        defaults=mapped,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except IntegrityError as exc:
                    if "fy_token" in str(exc) and "unique constraint" in str(exc).lower():
                        # Another instrument holds this fy_token. Free it up.
                        stale_inst = Instrument.objects.filter(fy_token=fy_token).exclude(sym_ticker=sym_ticker).first()
                        if stale_inst:
                            stale_inst.fy_token = f"STALE_{stale_inst.id}_{stale_inst.fy_token}"[:30]
                            stale_inst.is_active = False
                            stale_inst.save(update_fields=['fy_token', 'is_active'])
                            
                        # Try again
                        _, was_created = Instrument.objects.update_or_create(
                            sym_ticker=sym_ticker,
                            defaults=mapped,
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    else:
                        raise exc
            except Exception as exc:
                errors += 1
                if errors <= 10:
                    logger.warning("  Error processing %s: %s", sym_ticker, exc)

        return created, updated, errors, synced_tokens

    def _cleanup_stale_source(self, source_key, synced_tokens):
        stale_qs = (
            Instrument.objects
            .filter(**SOURCE_FILTERS[source_key], is_active=True)
            .exclude(fy_token__in=synced_tokens)
            .only("id", "fy_token", "sym_ticker")
        )

        deleted = 0
        deactivated_ids = []
        for instrument in stale_qs.iterator(chunk_size=1000):
            if _has_business_references(instrument):
                deactivated_ids.append(instrument.id)
                continue
            with transaction.atomic():
                instrument.delete()
            deleted += 1

        deactivated = 0
        if deactivated_ids:
            deactivated = Instrument.objects.filter(id__in=deactivated_ids).update(is_active=False)

        return deleted, deactivated
