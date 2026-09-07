"""
Common trading utilities shared by execution engines.

Eliminates code duplication for time/session checks, price-limit comparisons,
SL-distance calculation, and app-managed protection extraction from strategy
configurations.
"""
import logging
from functools import lru_cache
from datetime import datetime, time
from decimal import Decimal

from common.enums import Side
logger = logging.getLogger(__name__)


# ─── Named Constants ────────────────────────────────────────────────
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)
PRE_MARKET_END = time(9, 15)
MARKET_OPEN_WINDOW_END = time(15, 30)
MARKET_CLOSE_WINDOW_START = time(15, 30)
EOD_TIME = time(15, 30)

DEFAULT_SL_FALLBACK_PCT = 0.01  # 1% of entry price
DEFAULT_SLIPPAGE_PCT = Decimal("0.0005")
DEFAULT_RISK_PER_TRADE_AMOUNT = 1000.0
DEFAULT_CAPITAL_PERCENTAGE = 10.0


@lru_cache(maxsize=32)
def get_exchange_times(exchange='NSE'):
    """Get market open/close times from ExchangeConfig, with hardcoded fallback.

    Uses LRU cache internally to avoid repeated DB queries within the same process.
    Cache is reset on process restart.
    """
    try:
        from common.models import ExchangeConfig
        config = ExchangeConfig.objects.filter(
            exchange=exchange, is_active=True
        ).first()
        if config:
            return config.market_open, config.market_close
    except Exception as e:
        logger.debug(f'ExchangeConfig lookup failed for {exchange}, using defaults: {e}')

    # Fallback to hardcoded defaults
    return MARKET_OPEN_TIME, MARKET_CLOSE_TIME


# ─── Time / Session Helpers ─────────────────────────────────────────

def parse_time(value):
    """
    Parse a time value from various formats (time object, string).
    Returns None if the value cannot be parsed.
    """
    if not value:
        return None
    if isinstance(value, time):
        return value
    value_str = str(value)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value_str, fmt).time()
        except ValueError:
            continue
    return None


def matches_market_session(current_time, market_session):
    """
    Check if the current time falls within the specified market session.
    """
    if market_session in {None, "", "ALL"}:
        return True
    if market_session == "PRE_MARKET":
        return current_time < PRE_MARKET_END
    if market_session == "MARKET_OPEN":
        return MARKET_OPEN_TIME <= current_time <= MARKET_OPEN_WINDOW_END
    if market_session == "MARKET_CLOSE":
        return MARKET_CLOSE_WINDOW_START <= current_time <= MARKET_CLOSE_TIME
    return True


def minutes_since_session_open(current_time):
    """Minutes elapsed since market open (09:15)."""
    session_open = datetime.combine(datetime.today(), MARKET_OPEN_TIME)
    current_dt = datetime.combine(datetime.today(), current_time)
    return max(int((current_dt - session_open).total_seconds()) // 60, 0)


def minutes_until(current_time, cutoff_time):
    """Minutes remaining until a cutoff time. Returns -1 if cutoff has passed."""
    current_dt = datetime.combine(datetime.today(), current_time)
    cutoff_dt = datetime.combine(datetime.today(), cutoff_time)
    if cutoff_dt < current_dt:
        return -1
    return int((cutoff_dt - current_dt).total_seconds() / 60)


# ─── Public Helpers ───────────────────────────────────────────────────

def get_any_field(obj, key, default=None):
    """Get a field from either a dict or a Django model instance."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def to_float(value, default=0.0):
    """Safe float conversion."""
    if value is None:
        return default
    if isinstance(value, (float, int)):
        return float(value)
    if hasattr(value, "__float__"):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    """Safe integer conversion."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
