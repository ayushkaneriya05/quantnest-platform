import logging
from decimal import Decimal
from common.enums import Side, OperandType
from common.trading_utils import to_float, get_any_field

logger = logging.getLogger(__name__)

DEFAULT_SL_FALLBACK_PCT = 0.01  # 1% of entry price

# ─── SL Distance Extraction ─────────────────────────────────────────

def compute_sl_distance_from_config(strategy_config, entry_price):
    """
    Extract the effective stop-loss distance from a strategy's configuration.
    Works with both dict snapshots (backtest) and Django model instances (paper).

    Returns the SL distance in absolute price points, falling back to
    entry_price * DEFAULT_SL_FALLBACK_PCT if no SL rule is configured.
    """
    entry_price = to_float(entry_price, 0.0)
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
            for rule in _get_active_rules(group):
                level = _derive_static_stop_price(rule, side, entry_price)
                if level is not None:
                    stop_candidates.append(level)
                    stop_rule_types.append(get_any_field(rule, "operand_a_type"))
                else:
                    has_dynamic_stop = True
        elif group_type == "TARGET":
            for rule in _get_active_rules(group):
                level = _derive_static_target_price(rule, side, entry_price, sl_distance)
                if level is not None:
                    target_candidates.append(level)
                    target_rule_types.append(get_any_field(rule, "operand_a_type"))
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
        "sl_distance": sl_distance,
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
        rules = _get_active_rules(group)
        for rule in rules:
            distance = _sl_rule_to_distance(rule, entry_price)
            if distance and distance > 0:
                return distance

    return None


def _get_rule_groups(strategy_config):
    """Get STOP_LOSS rule groups from config (dict or model)."""
    if isinstance(strategy_config, dict):
        return [
            g for g in strategy_config.get("rule_groups", [])
            if (get_any_field(g, "rule_type") or get_any_field(g, "group_type")) == "STOP_LOSS"
            and get_any_field(g, "is_active", True)
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


def _get_active_rules(group):
    """Get active rules from a rule group (dict or model)."""
    if isinstance(group, dict):
        rules = group.get("rules", [])
        return [r for r in rules if get_any_field(r, "is_active", True)]
    if hasattr(group, "rules"):
        try:
            return list(group.rules.filter(is_active=True))
        except Exception:
            return []
    return []


def _sl_rule_to_distance(rule, entry_price):
    """Convert a single SL rule to an absolute price distance using the new Operand Architecture."""
    op_a = get_any_field(rule, "operand_a_type")
    
    if op_a == OperandType.POSITION_PNL_PERCENTAGE:
        val = 0.0
        op_b_params = get_any_field(rule, "operand_b_params")
        if isinstance(op_b_params, dict):
            val = to_float(op_b_params.get("value"), 0.0)
        return entry_price * (abs(val) / 100) if val != 0 else None

    if op_a == OperandType.POSITION_PNL_POINTS:
        val = 0.0
        op_b_params = get_any_field(rule, "operand_b_params")
        if isinstance(op_b_params, dict):
            val = to_float(op_b_params.get("value"), 0.0)
        return abs(val) if val != 0 else None

    return None


def _derive_static_stop_price(rule, side, entry_price):
    distance = _sl_rule_to_distance(rule, entry_price)
    if distance is None:
        return None
    if side == Side.BUY:
        return entry_price - distance
    return entry_price + distance


def _derive_static_target_price(rule, side, entry_price, sl_distance):
    op_a = get_any_field(rule, "operand_a_type")
    distance = None
    
    if op_a == OperandType.POSITION_PNL_PERCENTAGE:
        val = 0.0
        op_b_params = get_any_field(rule, "operand_b_params")
        if isinstance(op_b_params, dict):
            val = to_float(op_b_params.get("value"), 0.0)
        distance = entry_price * (abs(val) / 100) if val != 0 else None
    elif op_a == OperandType.POSITION_PNL_POINTS:
        val = 0.0
        op_b_params = get_any_field(rule, "operand_b_params")
        if isinstance(op_b_params, dict):
            val = to_float(op_b_params.get("value"), 0.0)
        distance = abs(val) if val != 0 else None
    elif op_a == OperandType.POSITION_RR_RATIO:
        val = 0.0
        op_b_params = get_any_field(rule, "operand_b_params")
        if isinstance(op_b_params, dict):
            val = to_float(op_b_params.get("value"), 0.0)
        distance = (sl_distance * abs(val)) if (sl_distance and sl_distance > 0 and val != 0) else None

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



