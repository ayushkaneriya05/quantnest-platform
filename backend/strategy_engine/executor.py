import logging
from django.utils import timezone

from common.enums import Side, OrderType
from common.trading_utils import get_any_field
from rules_engine.evaluator import RuleEvaluator

logger = logging.getLogger(__name__)

class StrategyExecutor:
    """
    Orchestrates the evaluation of a strategy against market data.
    Stateless and event-driven.
    """
    def __init__(self, config_snapshot, mtf_data=None, indicator_engine=None, mtf_indicator_engines=None):
        """
        Initializes the executor with a strategy configuration.
        """
        # Validate config snapshot completeness
        self._validate_config_snapshot(config_snapshot)
        
        self.config = config_snapshot
        self.mtf_data = mtf_data or {}
        self.indicator_engine = indicator_engine
        self.mtf_indicator_engines = mtf_indicator_engines or {}
        
        # Pre-cache order configs for speed
        self.entry_config = self.config.get("entry_order_config", {})
        self.exit_config = self.config.get("exit_order_config", {})

        self.time_rule = self.config.get("time_rule", {})
        self.special_event_filter = self.config.get("special_event_filter", {})
    
    def _validate_config_snapshot(self, config):
        """Validate config snapshot has required fields."""
        required_fields = [
            'name', 'strategy_type', 'market_type', 'exchange', 'instrument_type',
            'entry_order_config', 'exit_order_config', 'rule_groups', 'watchlist_instruments'
        ]
        missing = [field for field in required_fields if field not in config]
        if missing:
            raise ValueError(f"Config snapshot missing required fields: {missing}")
        return True


    def completed_signal_frame(self, bars_df):
        """
        Return the candles that are eligible for signal evaluation.
        Live/paper feeds often include the currently forming candle; strategy
        signals always evaluate on completed candles only.
        """
        if len(bars_df) > 1:
            return bars_df.iloc[:-1]
        return bars_df

    def _active_groups(self, rule_type):
        groups = self.config.get("rule_groups", []) or []
        selected = [
            group for group in groups
            if (
                get_any_field(group, "group_type") == rule_type
                or get_any_field(group, "rule_type") == rule_type
            )
            and get_any_field(group, "is_active", True)
        ]
        return sorted(selected, key=lambda group: get_any_field(group, "priority", 1) or 1)


    def evaluate_entry_signals(self, bars_df):
        """
        Pre-compute entry signals for ALL bars in ``bars_df``.

        Returns a dict of ``{timestamp: bool}`` where ``True`` means
        the entry rule groups fired at that bar.

        This is the **vectorised** counterpart of ``evaluate_entry_logic``
        (which only checks the last bar).  Used exclusively by the backtest
        engine to avoid per-bar Python loops for indicator computation.
        """
        import pandas as pd
        from rules_engine.evaluator import RuleEvaluator

        completed_df = self.completed_signal_frame(bars_df)
        completed_mtf_data = {
            tf: self.completed_signal_frame(df) for tf, df in self.mtf_data.items()
        } if self.mtf_data else {}

        evaluator = RuleEvaluator(
            completed_df,
            mtf_data=completed_mtf_data,
            indicator_engine=self.indicator_engine,
            mtf_indicator_engines=self.mtf_indicator_engines,
        )

        entry_groups = self._active_groups("ENTRY")

        if not entry_groups:
            return {}

        operator = self.entry_config.get("entry_group_operator", "OR")
        series_list = [evaluator.evaluate_group(g) for g in entry_groups]

        if not series_list:
            return {}

        combined = series_list[0]
        for s in series_list[1:]:
            if operator == "AND":
                combined = combined & s
            else:
                combined = combined | s

        # Return only True entries to keep the dict compact
        return {ts: True for ts, val in combined.items() if val}


    def evaluate_entry_logic(self, bars_df, timestamp, state, risk_stats):
        """
        Full entry logic evaluation including filters and signals.
        Returns: (should_enter, side, reason)
        """
        # 1. No Trade Zone
        if self.is_in_no_trade_zone(timestamp):
            return False, None, "No trade zone active"
            
        # 2. Cooldowns
        can_enter, block_reason = self.can_enter(risk_stats, timestamp)
        if not can_enter:
            return False, None, block_reason
            
        # 3. Signals
        completed_df = self.completed_signal_frame(bars_df)
        if completed_df.empty:
            return False, None, "No completed signal candle"
        completed_mtf_data = {
            tf: self.completed_signal_frame(df) for tf, df in self.mtf_data.items()
        } if self.mtf_data else {}
        
        completed_evaluator = RuleEvaluator(completed_df, mtf_data=completed_mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)
        
        entry_groups = self._active_groups("ENTRY")
        
        hit, reason = self._evaluate_entry_group_set(
            entry_groups,
            "ENTRY",
            state,
            completed_evaluator,
            operator=self.entry_config.get("entry_group_operator", "OR"),
        )
        
        if hit:
            side = self.entry_config.get("entry_side", "BUY")
            return True, side, reason
            
        return False, None, "No signal"


    def evaluate_exit_logic(self, position_state, bars_df):
        """
        Evaluate SL, Target, and other exit rules for an open position.
        """
        completed_df = self.completed_signal_frame(bars_df)
        if completed_df.empty:
            return False, None, 'EXIT_ALL', {}
        completed_mtf_data = {
            tf: self.completed_signal_frame(df) for tf, df in self.mtf_data.items()
        } if self.mtf_data else {}
        completed_evaluator = RuleEvaluator(completed_df, mtf_data=completed_mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)

        # 1. Evaluate Stop Loss Rules
        sl_groups = self._active_groups("STOP_LOSS")
        sl_hit, sl_reason, sl_action, sl_action_params = self._evaluate_exit_group_set(
            sl_groups,
            "STOP_LOSS",
            position_state,
            completed_evaluator,
            operator=self.exit_config.get("stop_loss_group_operator", "OR"),
        )
        if sl_hit:
            return True, sl_reason, sl_action, sl_action_params

        # 2. Evaluate Target Rules
        target_groups = self._active_groups("TARGET")
        target_hit, target_reason, target_action, target_action_params = self._evaluate_exit_group_set(
            target_groups,
            "TARGET",
            position_state,
            completed_evaluator,
            operator=self.exit_config.get("target_group_operator", "OR"),
        )
        if target_hit:
            return True, target_reason, target_action, target_action_params

        # 3. Evaluate Custom Exit Rules
        exit_groups = self._active_groups("EXIT")
        exit_hit, exit_reason, exit_action, exit_action_params = self._evaluate_exit_group_set(
            exit_groups,
            "EXIT",
            position_state,
            completed_evaluator,
            operator=self.exit_config.get("exit_group_operator", "OR"),
        )
        if exit_hit:
            return True, exit_reason, exit_action, exit_action_params

        return False, None, 'EXIT_ALL', {}


    def _evaluate_exit_group_set(self, groups, rule_type, state, completed_evaluator, operator="OR"):
        if not groups:
            return False, None, 'EXIT_ALL', {}

        hits = []
        reasons = []
        actions = []
        action_params_list = []
        
        for group in groups:
            res_series = completed_evaluator.evaluate_group(group, state=state)
            matched = False
            if not res_series.empty and bool(res_series.iloc[-1]):
                matched = True
            
            if matched:
                reason_str = f"{rule_type} group '{get_any_field(group, 'name', 'unnamed')}' met"
                action_str = get_any_field(group, 'action', 'EXIT_ALL')
                
                # Prevent already executed partial exits and breakevens from blocking other rules
                if action_str == 'MOVE_TO_BREAKEVEN' and state.get(f'breakeven_{reason_str}'):
                    matched = False
                elif action_str == 'PARTIAL_EXIT' and state.get(f'partial_exit_{reason_str}'):
                    matched = False

            hits.append(matched)
            if matched:
                reasons.append(reason_str)
                actions.append(action_str)
                action_params_list.append(get_any_field(group, 'action_params') or {})

        is_hit = all(hits) if operator == "AND" else any(hits)
        
        if is_hit:
            action_priority = {"EXIT_ALL": 0, "PARTIAL_EXIT": 1, "MOVE_TO_BREAKEVEN": 2}
            best_idx = min(range(len(actions)), key=lambda idx: action_priority.get(actions[idx], 99))
            return True, reasons[best_idx], actions[best_idx], action_params_list[best_idx]
            
        return False, None, 'EXIT_ALL', {}


    def _evaluate_entry_group_set(self, groups, rule_type, state, completed_evaluator, operator="OR"):
        if not groups:
            return False, None

        hits = []
        reasons = []
        
        for group in groups:
            res_series = completed_evaluator.evaluate_group(group, state=state)
            matched = False
            if not res_series.empty and bool(res_series.iloc[-1]):
                matched = True
            
            hits.append(matched)
            if matched:
                reason_str = f"{rule_type} group '{get_any_field(group, 'name', 'unnamed')}' met"
                reasons.append(reason_str)

        is_hit = all(hits) if operator == "AND" else any(hits)
        
        if is_hit:
            return True, reasons[0]
            
        return False, None


    def can_enter(self, stats, timestamp):
        """
        Check re-entry limits and cooldowns.
        Timestamps from Redis are stored as ISO strings; we always parse them
        to UTC-aware datetimes to prevent TypeError on subtraction.
        """
        from dateutil.parser import parse
        from django.utils import timezone as dj_timezone

        def _ensure_aware(dt):
            """Guarantee a datetime has tzinfo (default UTC)."""
            if dt is None:
                return None
            if isinstance(dt, str):
                dt = parse(dt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dj_timezone.utc)
            return dt

        last_exit = _ensure_aware(stats.get("last_exit_time"))
        last_entry = _ensure_aware(stats.get("last_entry_time"))

        # Make sure the reference timestamp is also aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=dj_timezone.utc)

        # Check universal trade cooldown against last entry AND last exit
        cooldown = self.entry_config.get("cooldown_seconds", 0)
        if cooldown > 0:
            if last_entry and (timestamp - last_entry).total_seconds() < int(cooldown):
                return False, "Trade cooldown active (since last entry)"
            if last_exit and (timestamp - last_exit).total_seconds() < int(cooldown):
                return False, "Trade cooldown active (since last exit)"

        return True, None


    def is_in_no_trade_zone(self, timestamp):
        """
        Checks time rules and special event filters.
        """
        time_rule = self.config.get("time_rule") or {}
        if time_rule:
            timestamp = self._localize_timestamp(timestamp, time_rule.get("timezone"))
            # Day Check
            day_name = timestamp.strftime("%A").upper()
            trading_days = [str(d).upper() for d in (time_rule.get("trading_days") or [])]
            if trading_days and day_name not in trading_days:
                return True
            
            # Market Session Check
            from common.trading_utils import matches_market_session
            session = time_rule.get("market_session", "ALL")
            # Time Range Check
            current_time = timestamp.time()
            from common.trading_utils import parse_time
            start = parse_time(time_rule.get("start_time"))
            end = parse_time(time_rule.get("end_time"))

            if start is None and end is None and not matches_market_session(current_time, session):
                return True
            if start and current_time < start: return True
            if end and current_time > end: return True

            # No Trade Windows
            for window in time_rule.get("no_trade_windows") or []:
                w_start = parse_time(window.get("start"))
                w_end = parse_time(window.get("end"))
                if w_start and w_end and w_start <= current_time <= w_end:
                    return True

        # Special Event Filters
        special = self.config.get("special_event_filter") or {}
        if special:
            custom_dates = set(special.get("custom_avoid_dates") or [])
            if timestamp.date().isoformat() in custom_dates:
                return True

            active_events = special.get("active_events_today", [])
            if not active_events:
                active_events = self._resolve_active_events(timestamp, special)
            
            if active_events:
                return True

        return False


    @staticmethod
    def _resolve_active_events(timestamp, special):
        active_events = []
        try:
            from marketdata.calendar_service import EventCalendarService

            current_date = timestamp.date()
            if special.get("avoid_earnings") and EventCalendarService.is_event_day(current_date, "EARNINGS"):
                active_events.append("EARNINGS")
            if special.get("avoid_news") and EventCalendarService.is_event_day(current_date, "NEWS"):
                active_events.append("NEWS")
            if special.get("avoid_rbi_policy") and EventCalendarService.is_event_day(current_date, "RBI_POLICY"):
                active_events.append("RBI_POLICY")
        except Exception as exc:
            logger.warning("Event calendar lookup failed during strategy evaluation: %s", exc)
        return active_events


    @staticmethod
    def _localize_timestamp(timestamp, timezone_name):
        if not timezone_name:
            return timestamp
        try:
            import pytz
            import datetime as dt
            target_tz = pytz.timezone(timezone_name)
            if timestamp.tzinfo is None:
                timestamp = timezone.make_aware(timestamp, dt.timezone.utc)
            return timestamp.astimezone(target_tz)
        except Exception as exc:
            logger.warning("Timezone localization failed for '%s': %s", timezone_name, exc)
            return timestamp


    def resolve_entry_order(self, price):
        """
        Build the entry order intent. Strategy execution currently supports
        market orders only; the price is an expected/reference price.
        """
        return OrderType.MARKET, float(price)
