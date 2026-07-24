import logging
from decimal import Decimal
from datetime import datetime
import pandas as pd
from django.utils import timezone

from common.enums import Side, OrderType, RuleType, OperandType
from rules_engine.evaluator import RuleEvaluator

logger = logging.getLogger(__name__)

class StrategyExecutor:
    """
    Orchestrates the evaluation of a strategy against market data.
    Stateless and event-driven.
    """
    def __init__(self, config_snapshot, candle_completion_rule=None, mtf_data=None, indicator_engine=None, mtf_indicator_engines=None):
        self.config = config_snapshot
        self.candle_completion_rule = candle_completion_rule or \
            self.config.get("time_rule", {}).get("candle_completion_rule", "ON_CLOSE")
        self.mtf_data = mtf_data or {}
        self.indicator_engine = indicator_engine
        self.mtf_indicator_engines = mtf_indicator_engines or {}
        
        # Pre-cache order configs for speed
        self.entry_config = self.config.get("entry_order_config", {})
        self.exit_config = self.config.get("exit_order_config", {})
        self.reentry_rule = self.config.get("reentry_rule", {})
        self.time_rule = self.config.get("time_rule", {})
        self.special_event_filter = self.config.get("special_event_filter", {})

    def completed_signal_frame(self, bars_df):
        """
        Return the candles that are eligible for signal evaluation.
        Live/paper feeds often include the currently forming candle; ON_CLOSE
        strategies should only evaluate the last completed candle.
        """
        if self.candle_completion_rule in ("ON_CLOSE", "ON_OPEN") and len(bars_df) > 1:
            return bars_df.iloc[:-1]
        return bars_df

    def evaluate_entry_signals(self, bars_df):
        """
        Evaluate all entry rule groups and return a boolean series of signals.
        """
        evaluator = RuleEvaluator(bars_df, candle_completion_rule=self.candle_completion_rule, mtf_data=self.mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)
        groups = self.config.get("rule_groups", [])
        entry_groups = [
            g for g in groups
            if (g.get("group_type") == "ENTRY" or g.get("rule_type") == "ENTRY")
            and g.get("is_active", True)
        ]
        
        if not entry_groups:
            return pd.Series(False, index=bars_df.index)

        operator = self.entry_config.get("entry_group_operator", "OR")
        
        results = [evaluator.evaluate_group(g) for g in entry_groups]
        combined = results[0]
        for res in results[1:]:
            combined = (combined | res) if operator == "OR" else (combined & res)
        
        return combined

    def evaluate_exit_logic(self, position_state, bars_df, timestamp):
        """
        Evaluate SL, Target, and other exit rules for an open position.
        """
        live_evaluator = RuleEvaluator(bars_df, candle_completion_rule=self.candle_completion_rule, mtf_data=self.mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)
        completed_df = self.completed_signal_frame(bars_df)
        completed_mtf_data = {
            tf: self.completed_signal_frame(df) for tf, df in self.mtf_data.items()
        } if self.mtf_data else {}
        completed_evaluator = RuleEvaluator(completed_df, candle_completion_rule=self.candle_completion_rule, mtf_data=completed_mtf_data, indicator_engine=self.indicator_engine, mtf_indicator_engines=self.mtf_indicator_engines)

        last_price = float(bars_df["close"].iloc[-1])
        groups = self.config.get("rule_groups", [])
        protected_hit, protected_reason = self._check_runtime_protection(position_state, last_price)
        if protected_hit:
            return True, protected_reason, 'EXIT_ALL', {}
        
        # 1. Evaluate EOD Squareoff
        eod_time_str = self.time_rule.get("end_time")
        if eod_time_str:
            from common.trading_utils import parse_time
            eod_time = parse_time(eod_time_str)
            if eod_time and timestamp.time() >= eod_time:
                return True, "EOD Squareoff reached", 'EXIT_ALL', {}

        # 2. Evaluate Stop Loss Rules
        sl_groups = [
            g for g in groups
            if (g.get("group_type") == "STOP_LOSS" or g.get("rule_type") == "STOP_LOSS")
            and g.get("is_active", True)
        ]
        sl_hit, sl_reason, sl_action, sl_action_params = self._evaluate_group_set(
            sl_groups,
            "STOP_LOSS",
            position_state,
            last_price,
            live_evaluator,
            completed_evaluator,
            timestamp,
            operator=self.exit_config.get("stop_loss_group_operator", "OR"),
        )
        if sl_hit:
            return True, sl_reason, sl_action, sl_action_params

        # 3. Evaluate Target Rules
        target_groups = [
            g for g in groups
            if (g.get("group_type") == "TARGET" or g.get("rule_type") == "TARGET")
            and g.get("is_active", True)
        ]
        target_hit, target_reason, target_action, target_action_params = self._evaluate_group_set(
            target_groups,
            "TARGET",
            position_state,
            last_price,
            live_evaluator,
            completed_evaluator,
            timestamp,
            operator=self.exit_config.get("target_group_operator", "OR"),
        )
        if target_hit:
            return True, target_reason, target_action, target_action_params

        # 4. Evaluate Custom Exit Rules
        exit_groups = [
            g for g in groups
            if (g.get("group_type") == "EXIT" or g.get("rule_type") == "EXIT")
            and g.get("is_active", True)
        ]
        exit_hit, exit_reason, exit_action, exit_action_params = self._evaluate_group_set(
            exit_groups,
            "EXIT",
            position_state,
            last_price,
            live_evaluator,
            completed_evaluator,
            timestamp,
            operator=self.exit_config.get("exit_group_operator", "OR"),
        )
        if exit_hit:
            return True, exit_reason, exit_action, exit_action_params

        return False, None, 'EXIT_ALL', {}

    def _evaluate_group_set(self, groups, rule_type, state, last_price, live_evaluator, completed_evaluator, timestamp, operator="OR"):
        if not groups:
            return False, None, 'EXIT_ALL', {}

        hits = []
        reasons = []
        actions = []
        action_params_list = []
        
        for group in groups:
            # We use completed_evaluator for exit rules just like entry rules, 
            # unless we specifically need live tick evaluation (not fully supported yet)
            res_series = completed_evaluator.evaluate_group(group, state=state)
            matched = False
            if not res_series.empty and bool(res_series.iloc[-1]):
                matched = True
            
            if matched:
                reason_str = f"{rule_type} group '{group.get('name', 'unnamed')}' met"
                action_str = group.get('action', 'EXIT_ALL')
                
                # Prevent already executed partial exits and breakevens from blocking other rules
                if action_str == 'MOVE_TO_BREAKEVEN' and state.get(f'breakeven_{reason_str}'):
                    matched = False
                elif action_str == 'PARTIAL_EXIT' and state.get(f'partial_exit_{reason_str}'):
                    matched = False

            hits.append(matched)
            if matched:
                reasons.append(reason_str)
                actions.append(action_str)
                action_params_list.append(group.get('action_params') or {})

        is_hit = all(hits) if operator == "AND" else any(hits)
        
        if is_hit:
            # If any matched action is EXIT_ALL, prioritize it over partials
            if 'EXIT_ALL' in actions:
                return True, reasons[0], 'EXIT_ALL', {}
            return True, reasons[0], actions[0], action_params_list[0]
            
        return False, None, 'EXIT_ALL', {}

    @staticmethod
    def _check_runtime_protection(state, last_price):
        stop_price = state.get("protected_stop_price")
        target_price = state.get("protected_target_price")
        side = state.get("side")

        if stop_price is not None:
            stop_price = float(stop_price)
            if side == Side.BUY and last_price <= stop_price:
                return True, "Protected stop-loss hit"
            if side == Side.SELL and last_price >= stop_price:
                return True, "Protected stop-loss hit"

        if target_price is not None:
            target_price = float(target_price)
            if side == Side.BUY and last_price >= target_price:
                return True, "Protected target hit"
            if side == Side.SELL and last_price <= target_price:
                return True, "Protected target hit"

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

        today_trades = stats.get("instrument_daily_trades", stats.get("daily_trades", 0))
        reentry = self.config.get("reentry_rule", {})

        if today_trades > 0:
            if not reentry.get("allow_reentry", True):
                return False, "Re-entry not allowed"

            if last_exit and reentry.get("reentry_cooldown_seconds"):
                if (timestamp - last_exit).total_seconds() < int(reentry["reentry_cooldown_seconds"]):
                    return False, "Re-entry cooldown active"

        # Check entry cooldown
        cooldown = self.entry_config.get("entry_cooldown_seconds", 0)
        if last_entry and (timestamp - last_entry).total_seconds() < int(cooldown):
            return False, "Entry cooldown active"

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
            if not matches_market_session(timestamp.time(), session):
                return True

            # Time Range Check
            current_time = timestamp.time()
            from common.trading_utils import parse_time
            start = parse_time(time_rule.get("start_time"))
            end = parse_time(time_rule.get("end_time"))
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
                if special.get("avoid_earnings") and "EARNINGS" in active_events: return True
                if special.get("avoid_news") and "NEWS" in active_events: return True
                if special.get("avoid_rbi_policy") and "RBI_POLICY" in active_events: return True

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
            logger.debug("Event calendar lookup failed during strategy evaluation: %s", exc)
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
        except Exception:
            return timestamp


    def resolve_entry_order(self, last_candle, execution_candle=None):
        """
        Calculates price and order type based on EntryOrderConfig (ExecutionStyle).
        """
        style = self.entry_config.get("execution_style", "LTP")
        offset = float(self.entry_config.get("price_offset") or 0)

        if execution_candle is not None and style in {"LTP", "MARKET_AT_CLOSE", "LIMIT_OFFSET", "AT_OPEN"}:
            last_candle = execution_candle

        close = float(last_candle["close"])
        high = float(last_candle["high"])
        low = float(last_candle["low"])
        open_ = float(last_candle.get("open", close))

        target_price = close
        trigger_price = None
        otype = OrderType.MARKET

        if style in ("LTP", "MARKET_AT_CLOSE"):
            target_price = close + offset
            otype = OrderType.MARKET
        elif style == "AT_OPEN":
            target_price = open_ + offset
            otype = OrderType.MARKET
        elif style == "LIMIT_OFFSET":
            target_price = close + offset
            otype = OrderType.LIMIT
        elif style == "STOP_BREAKOUT":
            side = self.entry_config.get("entry_side", "BUY")
            target_price = (high + offset) if side == "BUY" else (low - offset)
            trigger_price = target_price
            otype = OrderType.STOP_LIMIT

        return otype, target_price, trigger_price
