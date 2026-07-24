import logging
from decimal import Decimal

from common.enums import (
    AutoDisableTriggerType,
    QuantityType,
    Severity,
    ViolationAction,
    ViolationType,
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
        "risk_per_trade_amount": 1000,
        "risk_per_trade_percentage": 1,
        "max_daily_trades": 10,
        "max_open_positions": 5,
    }

    DEFAULT_RISK_PROFILE = {
        "max_daily_loss_amount": 0,
        "max_daily_loss_percentage": 5,
        "max_exposure_percentage": 80,
        "max_per_instrument_exposure": 10,
        "max_drawdown_percentage": 15,
        "alert_on_breach": True,
    }

    def __init__(self, portfolio_capital):
        self.portfolio_capital = to_float(portfolio_capital, 0.0)

    def calculate_quantity(self, strategy_config, entry_price, sl_distance=None, stats=None, lot_size=1):
        """
        Calculate position quantity based on PositionSizingRule.
        Supports Martingale (Loss Recovery) if consecutive losses are present.
        """
        sizing = self._get_sizing_config(strategy_config)
        method = get_any_field(sizing, "sizing_method", QuantityType.CAPITAL_BASED)
        entry_price = max(to_float(entry_price, 0.0), 0.0)

        # If sl_distance was not explicitly provided, try to extract it from config
        if sl_distance is None and method in {QuantityType.RISK_FIXED, QuantityType.RISK_PERCENTAGE}:
            sl_distance = compute_sl_distance_from_config(strategy_config, entry_price)
        else:
            sl_distance = to_float(sl_distance, 0.0)

        if entry_price <= 0:
            return 1

        quantity = 1

        if method == QuantityType.FIXED:
            quantity = to_int(get_any_field(sizing, "fixed_quantity", 1), 1)
        elif method == QuantityType.CAPITAL_BASED:
            capital_pct = to_float(get_any_field(sizing, "capital_percentage", 10), 10.0) / 100
            allocated_capital = self.portfolio_capital * max(capital_pct, 0.0)
            quantity = int(allocated_capital / entry_price)
        elif method == QuantityType.RISK_FIXED:
            risk_amount = to_float(get_any_field(sizing, "risk_per_trade_amount", 1000), 1000.0)
            quantity = int(risk_amount / self._effective_sl_distance(entry_price, sl_distance))
        elif method == QuantityType.RISK_PERCENTAGE:
            risk_pct = to_float(get_any_field(sizing, "risk_per_trade_percentage", 1), 1.0) / 100
            risk_amount = self.portfolio_capital * max(risk_pct, 0.0)
            quantity = int(risk_amount / self._effective_sl_distance(entry_price, sl_distance))
        elif method == QuantityType.VOLATILITY_ADJUSTED:
            risk_amount = to_float(get_any_field(sizing, "risk_per_trade_amount", 1000), 1000.0)
            atr_value = to_float(self._get_stat(stats, "atr", 0.0), 0.0)
            if atr_value > 0:
                quantity = int(risk_amount / atr_value)
            else:
                quantity = 1
        else:
            logger.warning("Unsupported sizing method %s, defaulting to 1", method)

        # Apply Martingale / Loss Recovery Multiplier
        if stats and "consecutive_losses" in stats:
            if get_any_field(sizing, "loss_recovery_mode", False):
                consecutive_losses = int(stats["consecutive_losses"])
                if consecutive_losses > 0:
                    multiplier = float(get_any_field(sizing, "loss_recovery_multiplier", 1.5))
                    # Quantity = Base * (Multiplier ^ ConsecutiveLosses)
                    quantity = int(quantity * (multiplier ** consecutive_losses))

        quantity = max(quantity or 1, 1)

        # Round to lot size for derivatives
        if lot_size and lot_size > 1:
            lots = int(quantity / lot_size)
            if lots < 1:
                lots = 1  # minimum 1 lot
            quantity = lots * lot_size

        return quantity


    def check_strategy_limits(self, strategy_config, stats):
        """
        Check strategy-specific trade limits from PositionSizingRule.
        """
        sizing = self._get_sizing_config(strategy_config)
        open_positions = self._get_stat(stats, "open_positions")
        daily_trades = self._get_stat(stats, "daily_trades")

        max_open = to_int(get_any_field(sizing, "max_open_positions", 5), 5)
        if open_positions >= max_open:
            return False, "Max open positions reached"

        max_daily = to_int(get_any_field(sizing, "max_daily_trades", 10), 10)
        if daily_trades >= max_daily:
            return False, "Max daily trades reached"

        return True, ""

    def check_portfolio_risk(self, risk_profile, stats):
        """
        Check portfolio-level limits from PortfolioRiskProfile.
        """
        profile = self._normalize_risk_profile(risk_profile)
        breaches = self._evaluate_portfolio_breaches(profile, stats)

        if not breaches:
            return True, ""

        first = breaches[0]
        return False, first["message"]

    def evaluate_portfolio_risk(self, risk_profile, stats):
        """
        Return structured portfolio breach details for all matching limits.
        """
        profile = self._normalize_risk_profile(risk_profile)
        breaches = self._evaluate_portfolio_breaches(profile, stats)
        action = self._portfolio_breach_action(profile, breaches)

        return {
            "ok": not breaches,
            "breached": bool(breaches),
            "action": action,
            "should_alert": bool(breaches) and bool(get_any_field(profile, "alert_on_breach", True)),
            "should_halt": bool(breaches),
            "breaches": breaches,
        }

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
            "requires_manual_review": any(item["require_manual_review"] for item in triggered),
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

    def create_violation_record_data(
        self,
        violation_type,
        threshold_value=None,
        actual_value=None,
        action_taken=None,
        severity=None,
        message=None,
    ):
        """
        Build normalized RiskViolation payload data for all ViolationType values.
        """
        violation_type = violation_type or ViolationType.HALT_TRIGGERED
        threshold_value = to_float(threshold_value, 0.0)
        actual_value = to_float(actual_value, 0.0)
        severity = severity or self._default_severity_for_violation(violation_type)
        action_taken = action_taken or self._default_action_for_violation(violation_type)
        message = message or self._default_violation_message(violation_type, threshold_value, actual_value)

        return {
            "violation_type": violation_type,
            "severity": severity,
            "message": message,
            "threshold_value": threshold_value,
            "actual_value": actual_value,
            "action_taken": action_taken,
        }

    def _evaluate_portfolio_breaches(self, risk_profile, stats):
        breaches = []
        daily_pnl = self._get_stat(stats, "daily_pnl")
        total_exposure = self._get_stat(stats, "total_exposure")
        drawdown = self._get_stat(stats, "drawdown")
        instrument_exposure = self._get_stat(stats, "instrument_exposure_pct")

        max_loss_amount = to_float(get_any_field(risk_profile, "max_daily_loss_amount"), 0.0)
        if max_loss_amount > 0 and daily_pnl <= -max_loss_amount:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.DAILY_LOSS,
                    threshold_value=max_loss_amount,
                    actual_value=abs(daily_pnl),
                    message=f"Daily loss limit ({self._format_number(max_loss_amount)}) breached",
                )
            )

        max_loss_percentage = to_float(get_any_field(risk_profile, "max_daily_loss_percentage", 5), 5.0)
        current_loss_pct = (abs(daily_pnl) / self.portfolio_capital) * 100 if daily_pnl < 0 and self.portfolio_capital > 0 else 0.0
        if max_loss_percentage > 0 and current_loss_pct >= max_loss_percentage:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.DAILY_LOSS,
                    threshold_value=max_loss_percentage,
                    actual_value=current_loss_pct,
                    message=f"Daily loss limit ({self._format_number(max_loss_percentage)}%) breached",
                )
            )
            
        max_profit_amount = to_float(get_any_field(risk_profile, "max_daily_profit_amount"), 0.0)
        if max_profit_amount > 0 and daily_pnl >= max_profit_amount:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.HALT_TRIGGERED,
                    threshold_value=max_profit_amount,
                    actual_value=daily_pnl,
                    message=f"Daily profit limit ({self._format_number(max_profit_amount)}) reached. Trading halted."
                )
            )

        max_profit_percentage = to_float(get_any_field(risk_profile, "max_daily_profit_percentage"), 0.0)
        current_profit_pct = (daily_pnl / self.portfolio_capital) * 100 if daily_pnl > 0 and self.portfolio_capital > 0 else 0.0
        if max_profit_percentage > 0 and current_profit_pct >= max_profit_percentage:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.HALT_TRIGGERED,
                    threshold_value=max_profit_percentage,
                    actual_value=current_profit_pct,
                    message=f"Daily profit limit ({self._format_number(max_profit_percentage)}%) reached. Trading halted."
                )
            )

        max_exposure_pct = to_float(get_any_field(risk_profile, "max_exposure_percentage", 80), 80.0)
        current_exposure_pct = (total_exposure / self.portfolio_capital) * 100 if self.portfolio_capital > 0 else 0.0
        if max_exposure_pct > 0 and current_exposure_pct >= max_exposure_pct:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.EXPOSURE,
                    threshold_value=max_exposure_pct,
                    actual_value=current_exposure_pct,
                    message=f"Portfolio exposure limit ({self._format_number(max_exposure_pct)}%) breached",
                )
            )

        max_per_instrument = to_float(get_any_field(risk_profile, "max_per_instrument_exposure", 10), 10.0)
        if max_per_instrument > 0 and instrument_exposure >= max_per_instrument:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.EXPOSURE,
                    threshold_value=max_per_instrument,
                    actual_value=instrument_exposure,
                    message=f"Per-instrument exposure limit ({self._format_number(max_per_instrument)}%) breached",
                )
            )

        max_drawdown = to_float(get_any_field(risk_profile, "max_drawdown_percentage", 15), 15.0)
        if max_drawdown > 0 and drawdown >= max_drawdown:
            breaches.append(
                self.create_violation_record_data(
                    ViolationType.DRAWDOWN,
                    threshold_value=max_drawdown,
                    actual_value=drawdown,
                    message=f"Portfolio drawdown limit ({self._format_number(max_drawdown)}%) breached",
                )
            )

        return breaches

    def _portfolio_breach_action(self, profile, breaches):
        if not breaches:
            return None
        if get_any_field(profile, "alert_on_breach", True):
            return ViolationAction.NOTIFIED
        return ViolationAction.LOGGED

    def _get_sizing_config(self, strategy_config):
        if not strategy_config:
            return dict(self.DEFAULT_SIZING)

        sizing = get_any_field(strategy_config, "position_sizing_rule")
        if sizing is None and isinstance(strategy_config, dict) and "sizing_method" in strategy_config:
            sizing = strategy_config
        if sizing is None:
            return dict(self.DEFAULT_SIZING)
        return sizing

    def _normalize_risk_profile(self, risk_profile):
        if not risk_profile:
            return dict(self.DEFAULT_RISK_PROFILE)
        return risk_profile

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
            "require_manual_review": bool(get_any_field(rule, "require_manual_review", True)),
        }

    def _default_severity_for_violation(self, violation_type):
        if violation_type in {ViolationType.DRAWDOWN, ViolationType.DAILY_LOSS, ViolationType.HALT_TRIGGERED}:
            return Severity.CRITICAL
        if violation_type in {ViolationType.EXPOSURE, ViolationType.POSITION_SIZE}:
            return Severity.WARNING
        return Severity.INFO

    def _default_action_for_violation(self, violation_type):
        if violation_type == ViolationType.HALT_TRIGGERED:
            return ViolationAction.HALTED
        if violation_type in {ViolationType.DAILY_LOSS, ViolationType.DRAWDOWN}:
            return ViolationAction.BLOCKED
        if violation_type in {ViolationType.EXPOSURE, ViolationType.POSITION_SIZE, ViolationType.MAX_TRADES}:
            return ViolationAction.NOTIFIED
        if violation_type == ViolationType.CONSECUTIVE_LOSS:
            return ViolationAction.DISABLED
        return ViolationAction.LOGGED

    def _default_violation_message(self, violation_type, threshold_value, actual_value):
        if violation_type == ViolationType.POSITION_SIZE:
            return f"Position size limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.DAILY_LOSS:
            return f"Daily loss limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.EXPOSURE:
            return f"Exposure limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.DRAWDOWN:
            return f"Drawdown limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.CONSECUTIVE_LOSS:
            return f"Consecutive loss limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.MAX_TRADES:
            return f"Max trades limit breached: {self._format_number(actual_value)} vs {self._format_number(threshold_value)}"
        if violation_type == ViolationType.HALT_TRIGGERED:
            return "Trade halt condition triggered"
        return "Risk violation detected"

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
