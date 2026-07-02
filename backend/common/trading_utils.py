"""
Common trading utilities shared by execution engines.

Eliminates code duplication for time/session checks, price-limit comparisons,
SL-distance calculation, and app-managed protection extraction from strategy
configurations.
"""
import logging
from datetime import datetime, time
from decimal import Decimal

from common.enums import Side, StopLossType, TargetType

logger = logging.getLogger(__name__)


# ─── Named Constants ────────────────────────────────────────────────
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)
PRE_MARKET_END = time(9, 15)
MARKET_OPEN_WINDOW_END = time(10, 30)
MARKET_CLOSE_WINDOW_START = time(14, 30)
EOD_TIME = time(15, 30)

DEFAULT_SL_FALLBACK_PCT = 0.01  # 1% of entry price
DEFAULT_SLIPPAGE_PCT = Decimal("0.0005")
DEFAULT_RISK_PER_TRADE_AMOUNT = 1000.0
DEFAULT_CAPITAL_PERCENTAGE = 10.0


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


def in_no_trade_window(current_time, windows):
    """
    Check if the current time falls within any no-trade window.
    `windows` is a list of dicts with 'start' and 'end' keys.
    """
    for window in (windows or []):
        start = parse_time(window.get("start"))
        end = parse_time(window.get("end"))
        if start and end and start <= current_time <= end:
            return True
    return False


def price_limit_hit(price, limit, side, is_stop):
    """
    Check if a price has hit a stop-loss or target limit.

    For a BUY position:
      - stop hit  = price <= limit
      - target hit = price >= limit
    For a SELL position:
      - stop hit  = price >= limit
      - target hit = price <= limit
    """
    if side == Side.BUY:
        return price <= limit if is_stop else price >= limit
    return price >= limit if is_stop else price <= limit


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


# ─── SL Distance Extraction ─────────────────────────────────────────

def compute_sl_distance_from_config(strategy_config, entry_price):
    """
    Extract the effective stop-loss distance from a strategy's configuration.
    Works with both dict snapshots (backtest) and Django model instances (paper).

    Returns the SL distance in absolute price points, falling back to
    entry_price * DEFAULT_SL_FALLBACK_PCT if no SL rule is configured.
    """
    entry_price = _to_float(entry_price, 0.0)
    if entry_price <= 0:
        return max(entry_price * DEFAULT_SL_FALLBACK_PCT, 0.01)

    sl_distance = _extract_from_config(strategy_config, entry_price)
    if sl_distance and sl_distance > 0:
        return sl_distance

    return max(entry_price * DEFAULT_SL_FALLBACK_PCT, 0.01)


def derive_protection_levels(strategy_config, side, entry_price):
    """
    Build static stop-loss / target levels that can be enforced by the app
    even when the broker adapter does not support native OCO/bracket orders.

    Dynamic rules such as indicator-based or time-based exits are flagged so
    the strategy engine can continue evaluating them from market data.
    """
    entry_price = to_float(entry_price, 0.0)
    side = Side.SELL if str(side).upper() == Side.SELL else Side.BUY
    if entry_price <= 0:
        return {
            "protected_stop_price": None,
            "protected_target_price": None,
            "stop_rule_type": None,
            "target_rule_type": None,
            "has_dynamic_stop": False,
            "has_dynamic_target": False,
        }

    groups = get_any_field(strategy_config, "rule_groups", []) or []
    stop_candidates = []
    target_candidates = []
    stop_rule_types = []
    target_rule_types = []
    has_dynamic_stop = False
    has_dynamic_target = False
    sl_distance = compute_sl_distance_from_config(strategy_config, entry_price)

    for group in groups:
        group_type = get_any_field(group, "group_type") or get_any_field(group, "rule_type")
        if group_type == "STOP_LOSS":
            for rule in _get_group_rule_list(group, "stop_loss_rules"):
                level = _derive_static_stop_price(rule, side, entry_price)
                if level is not None:
                    stop_candidates.append(level)
                    stop_rule_types.append(get_any_field(rule, "sl_type"))
                else:
                    has_dynamic_stop = True
        elif group_type == "TARGET":
            for rule in _get_group_rule_list(group, "target_rules"):
                level = _derive_static_target_price(rule, side, entry_price, sl_distance)
                if level is not None:
                    target_candidates.append(level)
                    target_rule_types.append(get_any_field(rule, "target_type"))
                else:
                    has_dynamic_target = True

    stop_price = _select_stop_price(stop_candidates, side)
    target_price = _select_target_price(target_candidates, side)
    return {
        "protected_stop_price": stop_price,
        "protected_target_price": target_price,
        "stop_rule_type": stop_rule_types[0] if stop_rule_types else None,
        "target_rule_type": target_rule_types[0] if target_rule_types else None,
        "has_dynamic_stop": has_dynamic_stop,
        "has_dynamic_target": has_dynamic_target,
    }


def _extract_from_config(strategy_config, entry_price):
    """
    Try to extract SL distance from rule groups in a strategy config.
    Supports both dict (backtest snapshot) and Django model (paper trading).
    """
    rule_groups = _get_rule_groups(strategy_config)
    if not rule_groups:
        return None

    for group in rule_groups:
        sl_rules = _get_sl_rules(group, strategy_config)
        for rule in sl_rules:
            distance = _sl_rule_to_distance(rule, entry_price)
            if distance and distance > 0:
                return distance

    return None


def _get_rule_groups(strategy_config):
    """Get STOP_LOSS rule groups from config (dict or model)."""
    if isinstance(strategy_config, dict):
        return [
            g for g in strategy_config.get("rule_groups", [])
            if (_get_field(g, "rule_type") or _get_field(g, "group_type")) == "STOP_LOSS"
            and _get_field(g, "is_active", True)
        ]
    # Django model
    if hasattr(strategy_config, "rule_groups"):
        try:
            return list(strategy_config.rule_groups.filter(
                rule_type="STOP_LOSS", is_active=True
            ))
        except Exception:
            return []
    return []


def _get_sl_rules(group, strategy_config):
    """Get stop loss rules from a rule group (dict or model)."""
    if isinstance(group, dict):
        rules = group.get("stop_loss_rules", [])
        return [r for r in rules if get_any_field(r, "is_active", True)]
    if hasattr(group, "stop_loss_rules"):
        try:
            return list(group.stop_loss_rules.filter(is_active=True))
        except Exception:
            return []
    return []


def _get_target_rules(group):
    """Get target rules from a rule group (dict or model)."""
    if isinstance(group, dict):
        rules = group.get("target_rules", [])
        return [r for r in rules if get_any_field(r, "is_active", True)]
    if hasattr(group, "target_rules"):
        try:
            return list(group.target_rules.filter(is_active=True))
        except Exception:
            return []
    return []


def _get_group_rule_list(group, explicit_attr):
    if explicit_attr == "stop_loss_rules":
        return _get_sl_rules(group, None)
    if explicit_attr == "target_rules":
        return _get_target_rules(group)
    return []


def _sl_rule_to_distance(rule, entry_price):
    """Convert a single SL rule to an absolute price distance."""
    sl_type = get_any_field(rule, "sl_type")

    if sl_type == StopLossType.FIXED_PERCENTAGE:
        pct = to_float(get_any_field(rule, "fixed_percentage"), 0.0)
        return entry_price * (pct / 100) if pct > 0 else None

    if sl_type == StopLossType.FIXED_POINTS:
        return to_float(get_any_field(rule, "fixed_points"), 0.0) or None

    if sl_type == StopLossType.TRAILING_PERCENTAGE:
        pct = to_float(get_any_field(rule, "trailing_value"), 0.0)
        return entry_price * (pct / 100) if pct > 0 else None

    if sl_type == StopLossType.TRAILING_FIXED:
        return to_float(get_any_field(rule, "trailing_value"), 0.0) or None

    if sl_type == StopLossType.EMERGENCY:
        pct = to_float(get_any_field(rule, "emergency_loss_pct"), 0.0)
        return entry_price * (pct / 100) if pct > 0 else None

    # Indicator-based, candle-based, time-based SLs cannot be pre-computed
    return None


def _derive_static_stop_price(rule, side, entry_price):
    sl_type = get_any_field(rule, "sl_type")
    distance = _sl_rule_to_distance(rule, entry_price)
    if distance is None:
        return None
    if side == Side.BUY:
        return entry_price - distance
    return entry_price + distance


def _derive_static_target_price(rule, side, entry_price, sl_distance):
    target_type = get_any_field(rule, "target_type")
    if target_type == TargetType.FIXED_PERCENTAGE:
        pct = to_float(get_any_field(rule, "fixed_percentage"), 0.0)
        distance = entry_price * (pct / 100) if pct > 0 else None
    elif target_type == TargetType.FIXED_POINTS:
        distance = to_float(get_any_field(rule, "fixed_points"), 0.0) or None
    elif target_type == TargetType.RISK_REWARD:
        ratio = to_float(get_any_field(rule, "risk_reward_ratio"), 0.0)
        distance = (sl_distance * ratio) if ratio > 0 and sl_distance > 0 else None
    else:
        return None

    if distance is None:
        return None
    if side == Side.BUY:
        return entry_price + distance
    return entry_price - distance


def _select_stop_price(prices, side):
    prices = [to_float(price, 0.0) for price in (prices or []) if price is not None]
    if not prices:
        return None
    if side == Side.BUY:
        return max(prices)
    return min(prices)


def _select_target_price(prices, side):
    prices = [to_float(price, 0.0) for price in (prices or []) if price is not None]
    if not prices:
        return None
    if side == Side.BUY:
        return min(prices)
    return max(prices)


# ─── Side Detection ──────────────────────────────────────────────────

def determine_entry_side(strategy_config):
    """
    Determine the trade entry side from strategy configuration.
    Works for both dict snapshots and Django models.
    """
    entry_config = get_any_field(strategy_config, "entry_order_config", {})
    side = get_any_field(entry_config, "entry_side", "BUY")
    return Side.SELL if str(side).upper() == "SELL" else Side.BUY


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


# Backward-compatible aliases used by older modules.
_to_float = to_float
_get_field = get_any_field
