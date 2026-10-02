"""Backtest-local strategy rule orchestration and exit actions."""

import logging
from dataclasses import dataclass, field
from datetime import timezone
from zoneinfo import ZoneInfo

from common.trading_utils import get_any_field, matches_market_session, parse_time
from rules_engine.evaluator import RuleEvaluator

logger = logging.getLogger(__name__)


class BacktestStrategyExecutor:
    """Evaluate strategy rules against the historical candles for one instrument."""

    def __init__(self, config, *, mtf_data=None, indicator_engine=None, mtf_indicator_engines=None, active_event_cache=None):
        self._validate_config_snapshot(config)
        self.config = config
        self.mtf_data = mtf_data or {}
        self.indicator_engine = indicator_engine
        self.mtf_indicator_engines = mtf_indicator_engines or {}
        self.entry_config = config.get("entry_order_config") or {}
        self.exit_config = config.get("exit_order_config") or {}
        self._groups = {}
        self._active_events_by_date = active_event_cache if active_event_cache is not None else {}

    @staticmethod
    def _validate_config_snapshot(config):
        required_fields = [
            'name', 'strategy_type', 'market_type', 'exchange', 'instrument_type', 'entry_order_config', 'exit_order_config',
            'rule_groups', 'watchlist_instruments', 'time_rule', 'special_event_filter', 'auto_disable_rules', 'position_sizing_rule'
        ]
        missing = [field for field in required_fields if field not in config]
        if missing:
            raise ValueError(f"Config snapshot missing required fields: {missing}")

    def _active_groups(self, group_type):
        if group_type not in self._groups:
            groups = self.config.get("rule_groups") or []
            self._groups[group_type] = sorted(
                (
                    group for group in groups
                    if (get_any_field(group, "group_type") == group_type
                        or get_any_field(group, "rule_type") == group_type)
                    and get_any_field(group, "is_active", True)
                ),
                key=lambda group: get_any_field(group, "priority", 1) or 1,
            )
        return self._groups[group_type]

    def evaluate_entry_signals(self, candles):
        groups = self._active_groups("ENTRY")
        if not groups:
            return {}
        evaluator = RuleEvaluator(candles, mtf_data=self.mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)
        signals = [evaluator.evaluate_group(group) for group in groups]
        combined = signals[0]
        for signal in signals[1:]:
            if self.entry_config.get("entry_group_operator", "OR") == "AND":
                combined = combined & signal
            else:
                combined = combined | signal
        return {timestamp: True for timestamp, matched in combined.items() if matched}

    def evaluate_exit_logic(self, position, candles):
        if candles.empty:
            return False, None, "EXIT_ALL", {}
        evaluator = RuleEvaluator(
            candles,
            mtf_data=self.mtf_data,
            indicator_engine=self.indicator_engine,
            mtf_indicator_engines=self.mtf_indicator_engines,
        )
        for group_type, operator_key in (
            ("STOP_LOSS", "stop_loss_group_operator"),
            ("TARGET", "target_group_operator"),
            ("EXIT", "exit_group_operator"),
        ):
            groups = self._active_groups(group_type)
            hit, reason, action, params = self._evaluate_exit_group_set(
                groups,
                group_type,
                position,
                evaluator,
                operator=self.exit_config.get(operator_key, "OR"),
            )
            if hit:
                return True, reason, action, params
        return False, None, "EXIT_ALL", {}

    def _evaluate_exit_group_set(self, groups, group_type, state, evaluator, operator="OR"):
        if not groups:
            return False, None, "EXIT_ALL", {}

        hits, reasons, actions, action_params = [], [], [], []
        for group in groups:
            result = evaluator.evaluate_group(group, state=state)
            matched = not result.empty and bool(result.iloc[-1])
            if matched:
                reason = f"{group_type} group '{get_any_field(group, 'name', 'unnamed')}' met"
                action = get_any_field(group, "action", "EXIT_ALL") or "EXIT_ALL"
                if action == "MOVE_TO_BREAKEVEN" and state.get(f"breakeven_{reason}"):
                    matched = False
                elif action == "PARTIAL_EXIT" and state.get(f"partial_exit_{reason}"):
                    matched = False

            if operator == "AND" and not matched:
                return False, None, "EXIT_ALL", {}
            if operator != "AND" and matched and action == "EXIT_ALL":
                return True, reason, action, get_any_field(group, "action_params") or {}

            hits.append(matched)
            if matched:
                reasons.append(reason)
                actions.append(action)
                action_params.append(get_any_field(group, "action_params") or {})

        triggered = all(hits) if operator == "AND" else any(hits)
        if triggered:
            priority = {"EXIT_ALL": 0, "PARTIAL_EXIT": 1, "MOVE_TO_BREAKEVEN": 2}
            selected = min(range(len(actions)), key=lambda index: priority.get(actions[index], 99))
            return True, reasons[selected], actions[selected], action_params[selected]
        return False, None, "EXIT_ALL", {}

    def can_enter(self, stats, timestamp):
        from dateutil.parser import parse

        def ensure_aware(value):
            if value is None:
                return None
            if isinstance(value, str):
                value = parse(value)
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value

        last_exit = ensure_aware(stats.get("last_exit_time"))
        last_entry = ensure_aware(stats.get("last_entry_time"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        cooldown = self.entry_config.get("cooldown_seconds", 0)
        if cooldown > 0:
            if last_entry and (timestamp - last_entry).total_seconds() < int(cooldown):
                return False, "Trade cooldown active (since last entry)"
            if last_exit and (timestamp - last_exit).total_seconds() < int(cooldown):
                return False, "Trade cooldown active (since last exit)"
        return True, None

    def is_in_no_trade_zone(self, timestamp):
        time_rule = self.config.get("time_rule") or {}
        if time_rule:
            timestamp = self._localize_timestamp(timestamp, time_rule.get("timezone"))
            day_name = timestamp.strftime("%A").upper()
            trading_days = [str(day).upper() for day in (time_rule.get("trading_days") or [])]
            if trading_days and day_name not in trading_days:
                return True

            current_time = timestamp.time()
            if not matches_market_session(current_time, time_rule.get("market_session", "ALL")):
                return True
            start, end = parse_time(time_rule.get("start_time")), parse_time(time_rule.get("end_time"))
            if start and current_time < start:
                return True
            if end and current_time > end:
                return True
            for window in time_rule.get("no_trade_windows") or []:
                start, end = parse_time(window.get("start")), parse_time(window.get("end"))
                if start and end and start <= current_time <= end:
                    return True

        special = self.config.get("special_event_filter") or {}
        if not special:
            return False
        if timestamp.date().isoformat() in set(special.get("custom_avoid_dates") or []):
            return True
        if timestamp.date() not in self._active_events_by_date:
            self._active_events_by_date[timestamp.date()] = self._resolve_active_events(timestamp, special)
        return bool(self._active_events_by_date[timestamp.date()])

    @staticmethod
    def _resolve_active_events(timestamp, special):
        active = []
        try:
            from marketdata.calendar_service import EventCalendarService

            for flag, event_type in (
                ("avoid_earnings", "EARNINGS"),
                ("avoid_news", "NEWS"),
                ("avoid_rbi_policy", "RBI_POLICY"),
            ):
                if special.get(flag) and EventCalendarService.is_event_day(timestamp.date(), event_type):
                    active.append(event_type)
        except Exception as exc:
            logger.warning("Event calendar lookup failed during backtest evaluation: %s", exc)
        return active

    @staticmethod
    def _localize_timestamp(timestamp, timezone_name):
        if not timezone_name:
            return timestamp
        try:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.astimezone(ZoneInfo(timezone_name))
        except Exception as exc:
            logger.warning("Timezone localization failed for '%s': %s", timezone_name, exc)
            return timestamp


@dataclass
class BacktestExitDecision:
    should_send_order: bool = False
    quantity: int = 0
    reason: str = ""
    state_updates: dict = field(default_factory=dict)


def process_exit_action(action, params, position, reason):
    """Translate a matched exit rule into a backtest order and state update."""
    params = params or {}
    if action == "MOVE_TO_BREAKEVEN":
        key = f"breakeven_{reason}"
        if position.get(key):
            return BacktestExitDecision()
        return BacktestExitDecision(state_updates={
            "protected_stop_price": position.get("avg_price"), key: True,
        })

    if action == "PARTIAL_EXIT":
        exit_pct = float(params.get("exit_pct", 50))
        key = f"partial_exit_{reason}"
        if position.get(key):
            return BacktestExitDecision()
        quantity = int(position.get("quantity", 0) * exit_pct / 100)
        return BacktestExitDecision(
            should_send_order=quantity > 0,
            quantity=quantity,
            reason=f"Partial Exit ({exit_pct}%): {reason}",
            state_updates={key: True},
        )

    quantity = int(position.get("quantity", 0))
    return BacktestExitDecision(
        should_send_order=quantity > 0,
        quantity=quantity,
        reason=reason,
    )
