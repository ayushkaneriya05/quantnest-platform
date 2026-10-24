import logging
import math
from common.enums import Side, OperandType, QuantityType

logger = logging.getLogger(__name__)

DEFAULT_SL_FALLBACK_PCT = 0.01  # 1% of entry price

# ─── SL Distance Extraction ─────────────────────────────────────────

def compute_sl_distance_from_config(strategy_config: dict, entry_price: float) -> float:
    """
    Extract the effective stop-loss distance from a strategy's configuration.
    Reads the immutable strategy snapshot used by every execution mode.

    Returns the SL distance in absolute price points, falling back to
    entry_price * DEFAULT_SL_FALLBACK_PCT if no SL rule is configured.
    """
    if entry_price <= 0:
        return max(entry_price * DEFAULT_SL_FALLBACK_PCT, 0.01)

    sl_distance = _extract_from_config(strategy_config, entry_price)
    if sl_distance and sl_distance > 0:
        return sl_distance

    return max(entry_price * DEFAULT_SL_FALLBACK_PCT, 0.01)


def derive_protection_levels(strategy_config: dict, side: str, entry_price: float) -> dict:
    """
    Build static stop-loss / target levels that can be enforced by the app
    even when the broker adapter does not support native OCO/bracket orders.

    Dynamic rules such as indicator-based or time-based exits are flagged so
    the strategy engine can continue evaluating them from market data.
    """
    if entry_price <= 0:
        return {
            "protected_stop_price": None,
            "protected_target_price": None,
            "stop_rule_type": None,
            "target_rule_type": None,
            "has_dynamic_stop": False,
            "has_dynamic_target": False,
        }

    groups = strategy_config.get("rule_groups", []) or []
    stop_candidates = []
    target_candidates = []
    stop_rule_types = []
    target_rule_types = []
    stop_inclusive, target_inclusive = {}, {}
    has_dynamic_stop = False
    has_dynamic_target = False
    sl_distance = compute_sl_distance_from_config(strategy_config, entry_price)

    for group in groups:
        if not group.get('is_active', True):
            continue
        group_type = group['rule_type']
        if group_type not in {'STOP_LOSS', 'TARGET'}:
            continue
        rules = _get_active_rules(group)
        operator = 'stop_loss_group_operator' if group_type == 'STOP_LOSS' else 'target_group_operator'
        exit_config = strategy_config.get('exit_order_config', {}) or {}
        peers = [item for item in groups if item.get('is_active', True) and
                 item['rule_type'] == group_type]
        # Only compile a complete, unconditional full-exit predicate. All other
        # groups retain their conditions in the shared rule evaluator.
        eligible = (len(rules) == 1 and
                    not (exit_config.get(operator, 'OR') == 'AND' and len(peers) > 1))
        if not eligible:
            has_dynamic_stop |= group_type == 'STOP_LOSS' and bool(rules)
            has_dynamic_target |= group_type == 'TARGET' and bool(rules)
            continue
        if group_type == "STOP_LOSS":
            for rule in rules:
                level = _derive_static_stop_price(rule, side, entry_price)
                if level is not None:
                    stop_candidates.append(level)
                    stop_rule_types.append(rule.get("operand_a_type"))
                    stop_inclusive[level] = stop_inclusive.get(level, False) or rule.get('comparison') == 'LTE'
                else:
                    has_dynamic_stop = True
        elif group_type == "TARGET":
            for rule in rules:
                level = _derive_static_target_price(rule, side, entry_price, sl_distance)
                if level is not None:
                    target_candidates.append(level)
                    target_rule_types.append(rule.get("operand_a_type"))
                    target_inclusive[level] = target_inclusive.get(level, False) or rule.get('comparison') == 'GTE'
                else:
                    has_dynamic_target = True

    stop_price = _select_stop_price(stop_candidates, side)
    target_price = _select_target_price(target_candidates, side)
    return {
        "protected_stop_price": stop_price,
        "protected_target_price": target_price,
        "protected_stop_inclusive": stop_inclusive.get(stop_price, True),
        "protected_target_inclusive": target_inclusive.get(target_price, True),
        "stop_rule_type": stop_rule_types[0] if stop_rule_types else None,
        "target_rule_type": target_rule_types[0] if target_rule_types else None,
        "has_dynamic_stop": has_dynamic_stop,
        "has_dynamic_target": has_dynamic_target,
        "sl_distance": sl_distance,
    }


def _extract_from_config(strategy_config, entry_price):
    """
    Try to extract SL distance from rule groups in a strategy config.
    Reads STOP_LOSS groups from a strategy snapshot.
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
    return [group for group in strategy_config.get('rule_groups', [])
            if group['rule_type'] == 'STOP_LOSS' and group.get('is_active', True)]


def _get_active_rules(group):
    return [rule for rule in group.get('rules', []) if rule.get('is_active', True)]


def _sl_rule_to_distance(rule, entry_price):
    """Convert a single SL rule to an absolute price distance using the new Operand Architecture."""
    op_a = rule.get("operand_a_type")
    if (rule.get('operand_b_type') != OperandType.CONSTANT or
            rule.get('comparison') not in {'LT', 'LTE'}):
        return None
    value = float(rule['operand_b_params']['value'])
    if not math.isfinite(value) or value >= 0:
        return None
    
    if op_a == OperandType.POSITION_PNL_PERCENTAGE:
        return entry_price * abs(value) / 100

    if op_a == OperandType.POSITION_PNL_POINTS:
        return abs(value)

    return None


def _derive_static_stop_price(rule, side, entry_price):
    distance = _sl_rule_to_distance(rule, entry_price)
    if distance is None:
        return None
    if side == Side.BUY:
        return entry_price - distance
    return entry_price + distance


def _derive_static_target_price(rule, side, entry_price, sl_distance):
    if (rule.get('operand_b_type') != OperandType.CONSTANT or
            rule.get('comparison') not in {'GT', 'GTE'}):
        return None
    value = float(rule['operand_b_params']['value'])
    if not math.isfinite(value) or value <= 0:
        return None
    op_a = rule.get("operand_a_type")
    distance = None
    
    if op_a == OperandType.POSITION_PNL_PERCENTAGE:
        distance = entry_price * value / 100
    elif op_a == OperandType.POSITION_PNL_POINTS:
        distance = value
    elif op_a == OperandType.POSITION_RR_RATIO:
        distance = sl_distance * value if sl_distance > 0 else None

    if distance is None:
        return None
    if side == Side.BUY:
        return entry_price + distance
    return entry_price - distance


def _select_stop_price(prices, side):
    if not prices:
        return None
    if side == Side.BUY:
        return max(prices)
    return min(prices)


def _select_target_price(prices, side):
    if not prices:
        return None
    if side == Side.BUY:
        return min(prices)
    return max(prices)

def calculate_quantity(sizing: dict, price: float, capital: float, *, lot_size: int, multiplier: float) -> int:
    """Calculate order units from fixed/capital sizing and round down to whole lots."""
    if not all(math.isfinite(value) and value > 0 for value in (price, multiplier, lot_size)):
        return 0
    method = sizing["sizing_method"]
    if method == QuantityType.FIXED:
        quantity = int(sizing["fixed_quantity"])
    elif method == QuantityType.CAPITAL_BASED:
        quantity = int(max(capital, 0) * float(sizing["capital_percentage"]) / 100 / (price * multiplier))
    else:
        raise ValueError(f"Unsupported sizing method: {method}")
    return max(quantity, 0) // lot_size * lot_size



