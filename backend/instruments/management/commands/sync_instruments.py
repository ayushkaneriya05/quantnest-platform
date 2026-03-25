"""
Management command to sync instrument master data from Fyers public JSON files.

Usage:
    py manage.py sync_instruments                   # Sync all sources
    py manage.py sync_instruments --source NSE_CM   # Sync one source
    py manage.py sync_instruments --source NSE_CM --source NSE_FO
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand
from instruments.models import Instrument

logger = logging.getLogger(__name__)

# ── Fyers JSON master file URLs ──
SOURCES = {
    'NSE_CM':  'https://public.fyers.in/sym_details/NSE_CM_sym_master.json',
    'NSE_FO':  'https://public.fyers.in/sym_details/NSE_FO_sym_master.json',
    'NSE_CD':  'https://public.fyers.in/sym_details/NSE_CD_sym_master.json',
    'NSE_COM': 'https://public.fyers.in/sym_details/NSE_COM_sym_master.json',
    'BSE_CM':  'https://public.fyers.in/sym_details/BSE_CM_sym_master.json',
    'BSE_FO':  'https://public.fyers.in/sym_details/BSE_FO_sym_master.json',
    'MCX_COM': 'https://public.fyers.in/sym_details/MCX_COM_sym_master.json',
}

# ── Fyers exchange code → our Exchange string ──
EXCHANGE_MAP = {10: 'NSE', 11: 'MCX', 12: 'BSE'}

# ── exInstType → our InstrumentType ──
# CD segment → always CURRENCY, COM segment → always COMMODITY
INST_TYPE_MAP = {
    # CM (Capital Market)
    0: 'STOCK',           # EQ (Equity)
    1: 'STOCK',           # Preference Shares
    2: 'BOND',            # Debentures
    3: 'STOCK',           # Warrants
    4: 'STOCK',           # Misc
    5: 'BOND',            # Sovereign Gold Bond
    6: 'BOND',            # Government Securities
    7: 'BOND',            # Treasury Bills
    8: 'MF',              # Mutual Fund
    9: 'ETF',             # Exchange Traded Fund
    10: 'INDEX', 50: 'STOCK',
    # FO (Equity Derivatives)
    11: 'FUTURE', 12: 'FUTURE', 13: 'FUTURE',
    14: 'OPTION', 15: 'OPTION',
    # CD (Currency Derivatives) — ALL classified as CURRENCY
    16: 'CURRENCY', 17: 'CURRENCY', 18: 'CURRENCY',
    19: 'CURRENCY',
    20: 'CURRENCY', 21: 'CURRENCY', 22: 'CURRENCY', 23: 'CURRENCY',
    24: 'CURRENCY', 25: 'CURRENCY',
    # COM (Commodity Derivatives) — ALL classified as COMMODITY
    30: 'COMMODITY', 31: 'COMMODITY', 32: 'COMMODITY',
    33: 'COMMODITY', 34: 'COMMODITY', 35: 'COMMODITY',
    36: 'COMMODITY', 37: 'COMMODITY',
}


def _safe_decimal(value, default=None):
    """Safely convert a value to Decimal."""
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _safe_int(value, default=None):
    """Safely convert a value to int."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_expiry(expiry_str):
    """Parse Fyers expiry date string (timestamp or empty) to date."""
    if not expiry_str or expiry_str == '':
        return None
    try:
        # Fyers sometimes sends epoch timestamp as string
        ts = int(expiry_str)
        if ts > 0:
            return datetime.fromtimestamp(ts).date()
    except (ValueError, TypeError, OSError):
        pass
    # Try YYYY-MM-DD format
    try:
        return datetime.strptime(expiry_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        pass
    return None


def _parse_last_update(date_str):
    """Parse lastUpdate field (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def map_entry(sym_ticker, data):
    """Map a single Fyers JSON entry to Instrument model fields."""
    ex_inst_type = _safe_int(data.get('exInstType'), 0)
    instrument_type = INST_TYPE_MAP.get(ex_inst_type, 'STOCK')
    exchange_code = data.get('exchange', 10)
    exchange = EXCHANGE_MAP.get(exchange_code, 'NSE')

    strike = _safe_decimal(data.get('strikePrice'))
    if strike is not None and strike < 0:
        strike = None

    qty_freeze = _safe_int(data.get('qtyFreeze'))

    return {
        'fy_token': data.get('fyToken', ''),
        'exchange_token': _safe_int(data.get('exToken'), 0),
        'symbol': data.get('exSymbol', ''),
        'name': (data.get('exSymName') or data.get('symDetails') or '')[:255],
        'sym_ticker': sym_ticker,
        'short_name': (data.get('short_name') or '')[:50],
        'display_name': (data.get('display_format_mob') or '')[:100],
        'description': (data.get('symbolDesc') or data.get('symDetails') or '')[:255],
        'isin': (data.get('isin') or '')[:20],
        'exchange': exchange,
        'segment': data.get('segment', 10),
        'series': (data.get('exSeries') or '')[:10],
        'ex_inst_type': ex_inst_type,
        'instrument_type': instrument_type,
        'option_type': (data.get('optType') or 'XX')[:5],
        'currency_code': (data.get('currencyCode') or 'INR')[:5],
        'strike_price': strike,
        'expiry_date': _parse_expiry(data.get('expiryDate')),
        'underlying_symbol': (data.get('underSym') or '')[:50],
        'underlying_fy_token': (data.get('underFyTok') or '')[:30],
        'lot_size': _safe_int(data.get('minLotSize'), 1),
        'tick_size': _safe_decimal(data.get('tickSize'), Decimal('0.05')),
        'qty_freeze': qty_freeze,
        'qty_multiplier': _safe_decimal(data.get('qtyMultiplier'), Decimal('1.0')),
        'face_value': _safe_decimal(data.get('faceValue')),
        'circuit_limit_upper': _safe_decimal(data.get('upperPrice')),
        'circuit_limit_lower': _safe_decimal(data.get('lowerPrice')),
        'trading_session': (data.get('tradingSession') or '')[:100],
        'previous_close': _safe_decimal(data.get('previousClose')),
        'previous_oi': _safe_decimal(data.get('previousOi')),
        'is_mtf_tradable': bool(data.get('is_mtf_tradable', 0)),
        'mtf_margin': _safe_decimal(data.get('mtf_margin')),
        'asm_gsm_flag': (data.get('asmGsmVal') or '')[:100],
        'has_options': bool(data.get('has_options', False)),
        'has_futures': bool(data.get('has_futures', False)),
        'stream': (data.get('stream') or '')[:20],
        'is_tradeable': bool(data.get('tradeStatus', 1)),
        'is_active': True,
        'last_sync_date': _parse_last_update(data.get('lastUpdate')),
    }


class Command(BaseCommand):
    help = 'Sync instrument master data from Fyers public JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            action='append',
            choices=list(SOURCES.keys()),
            help='Specific source(s) to sync (e.g. NSE_CM, NSE_FO). Omit to sync all.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate without writing to database.',
        )

    def handle(self, *args, **options):
        sources = options['source'] or list(SOURCES.keys())
        dry_run = options['dry_run']
        total_created = 0
        total_updated = 0
        total_errors = 0

        for source_key in sources:
            url = SOURCES[source_key]
            self.stdout.write(f'\n── Syncing {source_key} from {url}')

            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                self.stderr.write(self.style.ERROR(f'  Failed to download {source_key}: {e}'))
                total_errors += 1
                continue
            except ValueError as e:
                self.stderr.write(self.style.ERROR(f'  Failed to parse JSON for {source_key}: {e}'))
                total_errors += 1
                continue

            self.stdout.write(f'  Downloaded {len(data)} entries')

            created = 0
            updated = 0
            errors = 0

            for sym_ticker, entry in data.items():
                try:
                    mapped = map_entry(sym_ticker, entry)
                    fy_token = mapped.pop('fy_token')

                    if not fy_token:
                        errors += 1
                        continue

                    if dry_run:
                        created += 1
                        continue

                    _, was_created = Instrument.objects.update_or_create(
                        fy_token=fy_token,
                        defaults=mapped,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        logger.warning(f'  Error processing {sym_ticker}: {e}')

            prefix = '[DRY RUN] ' if dry_run else ''
            self.stdout.write(self.style.SUCCESS(
                f'  {prefix}{source_key}: {created} created, {updated} updated, {errors} errors'
            ))
            total_created += created
            total_updated += updated
            total_errors += errors

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Sync complete: {total_created} created, {total_updated} updated, {total_errors} errors'
        ))
