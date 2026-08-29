import logging
from common.enums import (
    AutoDisableTriggerType,
    QuantityType,
)
from common.trading_utils import get_any_field, to_float, to_int
from rules_engine.utils import compute_sl_distance_from_config

logger = logging.getLogger(__name__)


class RiskEvaluator:
    """
    Evaluates risk rules and calculates position sizing during backtesting.
    Supports both Django model instances and dict snapshots.
    """

    DEFAULT_SIZING = {
        "sizing_method": QuantityType.CAPITAL_BASED,
        "fixed_quantity": 1,
        "capital_percentage": 10,
        "risk_per_trade_percentage": 1,
    }

    def __init__(self, portfolio_capital):
        self.portfolio_capital = to_float(portfolio_capital, 0.0)

    def calculate_quantity(self, sizing_config, entry_price, sl_distance=None, lot_size=1, strategy_config=None):
        """
        Calculate position quantity based on PositionSizingRule.
        
        Args:
            sizing_config: Can be either:
                - Full strategy config dict with nested 'position_sizing_rule' key
                - Route-level sizing dict with direct 'sizing_method' key
                - None (uses default sizing)
            strategy_config: Full strategy config with rule_groups (needed for SL distance extraction).
                             If None, sizing_config will be used as fallback.
        """
        sizing = self._get_sizing_config(sizing_config)
        method = get_any_field(sizing, "sizing_method", QuantityType.CAPITAL_BASED)
        entry_price = max(to_float(entry_price, 0.0), 0.0)

        # If sl_distance was not explicitly provided, try to extract it from config
        if sl_distance is None and method == QuantityType.RISK_BASED:
            # Use strategy_config for SL extraction (has rule_groups), fallback to sizing_config
            sl_distance = compute_sl_distance_from_config(strategy_config, entry_price)
        else:
            sl_distance = to_float(sl_distance, 0.0)

        if entry_price <= 0:
            return 0

        quantity = 0

        if method == QuantityType.FIXED:
            quantity = to_int(get_any_field(sizing, "fixed_quantity", 1), 1)
        elif method == QuantityType.CAPITAL_BASED:
            capital_pct = to_float(get_any_field(sizing, "capital_percentage", 10), 10.0) / 100
            allocated_capital = self.portfolio_capital * max(capital_pct, 0.0)
            quantity = int(allocated_capital / entry_price)
        elif method == QuantityType.RISK_BASED:
            risk_pct = to_float(get_any_field(sizing, "risk_per_trade_percentage", 1), 1.0) / 100
            risk_amount = self.portfolio_capital * max(risk_pct, 0.0)
            quantity = int(risk_amount / self._effective_sl_distance(entry_price, sl_distance))
        else:
            logger.warning("Unsupported sizing method %s, rejecting order with quantity 0", method)

        quantity = max(int(quantity or 0), 0)

        # Round to lot size for derivatives
        if lot_size and lot_size > 1:
            lots = int(quantity / lot_size)
            if lots < 1:
                return 0
            quantity = lots * lot_size

        return quantity
    

    def evaluate_auto_disable_rules(self, rules, stats):
        """
        Evaluate a list/queryset of StrategyAutoDisable rules.
        """
        rule_list = list(rules or [])
        triggered = []

        for rule in rule_list:
            result = self.evaluate_auto_disable_rule(rule, stats)
            if result["triggered"]:
                triggered.append(result)

        return {
            "triggered": bool(triggered),
            "matches": triggered,
            "should_disable": bool(triggered),
            "can_auto_reenable": any(item["auto_reenable"] for item in triggered),
            "max_cooldown_hours": max((item["cooldown_hours"] for item in triggered), default=0),
        }

    def evaluate_auto_disable_rule(self, rule, stats):
        """
        Evaluate a single StrategyAutoDisable rule for all AutoDisableTriggerType values.
        """
        if not get_any_field(rule, "is_active", True):
            return self._auto_disable_result(rule, False, None, None, "Rule is inactive")

        trigger_type = get_any_field(rule, "trigger_type")
        threshold_value = to_float(get_any_field(rule, "threshold_value"), 0.0)
        threshold_count = to_int(get_any_field(rule, "threshold_count"), 0)

        current_value = None
        triggered = False
        message = ""

        if trigger_type == AutoDisableTriggerType.CONSECUTIVE_LOSSES:
            current_value = self._get_stat(stats, "consecutive_losses")
            triggered = threshold_count > 0 and current_value >= threshold_count
            message = f"Consecutive losses reached {self._format_number(current_value)}"
        elif trigger_type == AutoDisableTriggerType.CONSECUTIVE_WINS:
            current_value = self._get_stat(stats, "consecutive_wins")
            triggered = threshold_count > 0 and current_value >= threshold_count
            message = f"Consecutive wins reached {self._format_number(current_value)}"
        elif trigger_type == AutoDisableTriggerType.DAILY_LOSS:
            daily_pnl = self._get_stat(stats, "daily_pnl")
            current_value = (abs(daily_pnl) / self.portfolio_capital) * 100 if daily_pnl < 0 and self.portfolio_capital > 0 else 0.0
            triggered = threshold_value > 0 and current_value >= threshold_value
            message = f"Daily loss reached {self._format_number(current_value)}%"
        elif trigger_type == AutoDisableTriggerType.WEEKLY_LOSS:
            weekly_pnl = self._get_stat(stats, "weekly_pnl")
            current_value = (abs(weekly_pnl) / self.portfolio_capital) * 100 if weekly_pnl < 0 and self.portfolio_capital > 0 else 0.0
            triggered = threshold_value > 0 and current_value >= threshold_value
            message = f"Weekly loss reached {self._format_number(current_value)}%"
        elif trigger_type == AutoDisableTriggerType.MONTHLY_LOSS:
            monthly_pnl = self._get_stat(stats, "monthly_pnl")
            current_value = (abs(monthly_pnl) / self.portfolio_capital) * 100 if monthly_pnl < 0 and self.portfolio_capital > 0 else 0.0
            triggered = threshold_value > 0 and current_value >= threshold_value
            message = f"Monthly loss reached {self._format_number(current_value)}%"
        elif trigger_type == AutoDisableTriggerType.WIN_RATE_DROP:
            if self._get_stat(stats, "total_closed_trades", self._get_stat(stats, "closed_trades", 0)) <= 0:
                return self._auto_disable_result(rule, False, None, threshold_value, "No completed trades")
            current_value = self._get_stat(stats, "win_rate")
            triggered = threshold_value > 0 and current_value <= threshold_value
            message = f"Win rate dropped to {self._format_number(current_value)}%"
        elif trigger_type == AutoDisableTriggerType.DRAWDOWN:
            current_value = self._get_stat(stats, "drawdown")
            triggered = threshold_value > 0 and current_value >= threshold_value
            message = f"Drawdown reached {self._format_number(current_value)}%"
        else:
            logger.warning("Unsupported auto disable trigger type: %s", trigger_type)

        if not triggered and not message:
            message = "Rule not triggered"

        return self._auto_disable_result(rule, triggered, current_value, threshold_value or threshold_count, message)

    def _get_sizing_config(self, sizing_config):
        """
        Extract sizing configuration from either strategy config or route-level override.
        
        Args:
            sizing_config: Can be:
                - Full strategy config dict with nested 'position_sizing_rule'
                - Route-level sizing dict with direct 'sizing_method'
                - None (uses default)
        
        Returns:
            Sizing configuration dict
        """
        # Case 1: Full strategy config with nested position_sizing_rule
        if sizing_config and isinstance(sizing_config, dict):
            if "position_sizing_rule" in sizing_config:
                return sizing_config["position_sizing_rule"]
            # Case 2: Route-level sizing dict (flat structure with sizing_method)
            if "sizing_method" in sizing_config:
                return sizing_config
        # Case 3: None or invalid - use default
        return dict(self.DEFAULT_SIZING)

    def _auto_disable_result(self, rule, triggered, actual_value, threshold, message):
        trigger_type = get_any_field(rule, "trigger_type")
        return {
            "triggered": triggered,
            "trigger_type": trigger_type,
            "rule_name": get_any_field(rule, "name", trigger_type),
            "message": message,
            "actual_value": actual_value,
            "threshold": threshold,
            "auto_reenable": bool(get_any_field(rule, "auto_reenable", False)),
            "cooldown_hours": to_int(get_any_field(rule, "cooldown_hours", 24), 24),
        }

    def _effective_sl_distance(self, entry_price, sl_distance):
        if sl_distance and sl_distance > 0:
            return sl_distance
        return max(entry_price * 0.01, 0.01)

    def _get_stat(self, stats, key, default=0.0):
        if isinstance(stats, dict):
            return to_float(stats.get(key, default), default)
        return to_float(getattr(stats, key, default), default)

    def _format_number(self, value):
        value = to_float(value, 0.0)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}"