import logging
from decimal import Decimal
from datetime import datetime
import pandas as pd
from django.utils import timezone

from common.enums import Side, OrderType, StopLossType, TargetType
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
            return True, protected_reason
        
        # 1. Evaluate EOD Squareoff
        eod_time_str = self.time_rule.get("eod_squareoff_time") or self._extract_eod_squareoff_time(groups)
        if eod_time_str:
            from common.trading_utils import parse_time
            eod_time = parse_time(eod_time_str)
            if eod_time and timestamp.time() >= eod_time:
                return True, "EOD Squareoff reached"

        # 2. Evaluate Stop Loss Rules
        sl_groups = [
            g for g in groups
            if (g.get("group_type") == "STOP_LOSS" or g.get("rule_type") == "STOP_LOSS")
            and g.get("is_active", True)
        ]
        sl_hit, sl_reason = self._evaluate_group_set(
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
            return True, sl_reason

        # 3. Evaluate Target Rules
        target_groups = [
            g for g in groups
            if (g.get("group_type") == "TARGET" or g.get("rule_type") == "TARGET")
            and g.get("is_active", True)
        ]
        target_hit, target_reason = self._evaluate_group_set(
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
            return True, target_reason

        # 4. Evaluate Custom Exit Rules
        exit_groups = [
            g for g in groups
            if (g.get("group_type") == "EXIT" or g.get("rule_type") == "EXIT")
            and g.get("is_active", True)
        ]
        if exit_groups:
            operator = self.exit_config.get("exit_group_operator", "OR")
            results = [completed_evaluator.evaluate_group(g) for g in exit_groups]
            combined = results[0]
            for res in results[1:]:
                combined = (combined | res) if operator == "OR" else (combined & res)
            if not combined.empty and bool(combined.iloc[-1]):
                return True, "Custom Exit Rule Met"

        return False, None

    def _evaluate_group_set(self, groups, rule_type, state, last_price, live_evaluator, completed_evaluator, timestamp, operator="OR"):
        if not groups:
            return False, None

        hits = []
        reasons = []
        for group in groups:
            matched, reason = self._check_sl_target_rules(group, rule_type, state, last_price, live_evaluator, completed_evaluator, timestamp)
            hits.append(bool(matched))
            if matched and reason:
                reasons.append(reason)

        is_hit = all(hits) if operator == "AND" else any(hits)
        return is_hit, reasons[0] if reasons else None

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

    def _check_sl_target_rules(self, group, rule_type, state, last_price, live_evaluator, completed_evaluator, timestamp):
        if rule_type == "STOP_LOSS":
            rules = group.get("stop_loss_rules", []) or group.get("rules", [])
        elif rule_type == "TARGET":
            rules = group.get("target_rules", []) or group.get("rules", [])
        else:
            rules = group.get("rules", [])
        operator = group.get("logical_operator", "OR")
        
        hits = []
        first_reason = None
        
        for rule in rules:
            if not rule.get("is_active", True): continue
            
            matched = False
            type_ = rule.get("sl_type") if rule_type == "STOP_LOSS" else rule.get("target_type")
            
            # Implementation of various SL/Target types (Points, %, Trailing, Indicator)
            if type_ in {StopLossType.FIXED_POINTS, TargetType.FIXED_POINTS}:
                pts = self._numeric_rule_value(rule, "fixed_points", "value")
                diff = last_price - float(state["avg_price"])
                if state["side"] == Side.BUY:
                    matched = diff <= -pts if rule_type == "STOP_LOSS" else diff >= pts
                else:
                    matched = diff >= pts if rule_type == "STOP_LOSS" else diff <= -pts
            
            elif type_ in {StopLossType.FIXED_PERCENTAGE, TargetType.FIXED_PERCENTAGE}:
                pct = self._numeric_rule_value(rule, "fixed_percentage", "value") / 100.0
                price_move = (last_price / float(state["avg_price"])) - 1
                if state["side"] == Side.BUY:
                    matched = price_move <= -pct if rule_type == "STOP_LOSS" else price_move >= pct
                else:
                    matched = price_move >= pct if rule_type == "STOP_LOSS" else price_move <= -pct

            elif type_ in {StopLossType.INDICATOR_BASED, TargetType.INDICATOR_BASED}:
                # Custom indicator-based SL/Target
                # Adapt SL/Target schema to standard Rule schema for the evaluator
                adapted_rule = dict(rule)
                adapted_rule["comparison"] = rule.get("operator", "GREATER")
                adapted_rule["value"] = rule.get("threshold_value")
                adapted_rule["value2"] = rule.get("threshold_value2")
                adapted_rule["params"] = rule.get("indicator_params", {})
                
                res_series = completed_evaluator._evaluate_indicator_rule(adapted_rule)
                matched = bool(res_series.iloc[-1]) if not res_series.empty else False

            elif "TRAILING" in str(type_):
                # Trailing SL/Target logic
                is_pct = "PERCENTAGE" in str(type_)
                is_indicator = "INDICATOR" in str(type_)
                
                # Update trailing peak/trough in state
                peak = float(state.get("peak_price", state["avg_price"]))
                
                if is_indicator:
                    # Trailing based on an indicator (e.g. SuperTrend or ATR offset)
                    itype = rule.get("indicator_type")
                    params = rule.get("indicator_params", {})
                    # For trailing indicator, we often use the indicator value directly as the stop
                    indicator_val = completed_evaluator.indicator_engine.get_series(itype, params).iloc[-1]
                    
                    if state["side"] == Side.BUY:
                        # If price moves up, we might move stop up, but never down
                        current_stop = float(state.get("trailing_stop", 0))
                        new_stop = max(current_stop, indicator_val)
                        state["trailing_stop"] = new_stop
                        matched = last_price <= new_stop
                    else:
                        current_stop = float(state.get("trailing_stop", 9999999))
                        new_stop = min(current_stop, indicator_val)
                        state["trailing_stop"] = new_stop
                        matched = last_price >= new_stop
                else:
                    trail_val = float(rule.get("trailing_value") or 0)
                    if state["side"] == Side.BUY:
                        state["peak_price"] = max(peak, last_price)
                        threshold = state["peak_price"] * (1 - trail_val/100) if is_pct else state["peak_price"] - trail_val
                        matched = last_price <= threshold
                    else:
                        state["peak_price"] = min(peak, last_price)
                        threshold = state["peak_price"] * (1 + trail_val/100) if is_pct else state["peak_price"] + trail_val
                        matched = last_price >= threshold


            elif type_ == StopLossType.TIME_BASED or type_ == TargetType.TIME_BASED:
                # Exit after X minutes
                entry_time = state.get("entry_time")
                if entry_time:
                    if isinstance(entry_time, str):
                        from dateutil.parser import parse
                        entry_time = parse(entry_time)
                    minutes_limit = int(rule.get("time_minutes") or rule.get("time_exit_minutes") or 0)
                    if minutes_limit > 0 and (timestamp - entry_time).total_seconds() >= minutes_limit * 60:
                        matched = True

            elif type_ == StopLossType.EMERGENCY:
                # Emergency exit if loss exceeds this %
                emergency_pct = self._numeric_rule_value(rule, "emergency_loss_pct") / 100.0
                price_move = (last_price / float(state["avg_price"])) - 1
                if state["side"] == Side.BUY:
                    matched = price_move <= -emergency_pct
                else:
                    matched = price_move >= emergency_pct

            elif type_ == StopLossType.CANDLE_BASED:
                # SL at High/Low of previous X candles
                lookback = int(rule.get("candle_lookback") or 1)
                offset = int(rule.get("candle_offset") or 1)
                part = rule.get("candle_part", "LOW" if state["side"] == Side.BUY else "HIGH")
                
                bars = live_evaluator.df
                if len(bars) > offset + lookback:
                    target_bars = bars.iloc[-(offset + lookback):-offset]
                    if state["side"] == Side.BUY:
                        sl_price = float(target_bars["low"].min())
                        matched = last_price <= sl_price
                    else:
                        sl_price = float(target_bars["high"].max())
                        matched = last_price >= sl_price

            elif type_ == TargetType.RISK_REWARD:
                # Target = SL * ratio
                ratio = self._numeric_rule_value(rule, "risk_reward_ratio", default=2.0)
                sl_dist = float(state.get("sl_distance", 0))
                if sl_dist > 0:
                    pts_to_target = sl_dist * ratio
                    diff = last_price - float(state["avg_price"])
                    if state["side"] == Side.BUY:
                        matched = diff >= pts_to_target
                    else:
                        matched = diff <= -pts_to_target

            elif type_ == TargetType.EXPIRY:
                # Exit X minutes before instrument expiry date (F&O contracts)
                expiry_date = state.get("instrument_expiry_date")
                if expiry_date is not None:
                    from datetime import date as date_type
                    if isinstance(expiry_date, str):
                        try:
                            expiry_date = date_type.fromisoformat(expiry_date)
                        except (ValueError, TypeError):
                            expiry_date = None
                    if expiry_date and timestamp.date() == expiry_date:
                        minutes_before = int(rule.get("expiry_exit_minutes_before") or rule.get("time_minutes") or 30)
                        import datetime as dt_module
                        # Indian market close = 15:30 IST
                        market_close = dt_module.time(15, 30)
                        cutoff = (dt_module.datetime.combine(expiry_date, market_close) - dt_module.timedelta(minutes=minutes_before)).time()
                        if timestamp.time() >= cutoff:
                            matched = True

            elif type_ == TargetType.EOD:
                # Per-rule EOD squareoff time
                eod_time_str = rule.get("eod_squareoff_time") or rule.get("value")
                if eod_time_str:
                    from common.trading_utils import parse_time
                    eod_time = parse_time(eod_time_str)
                    if eod_time and timestamp.time() >= eod_time:
                        matched = True

            hits.append(matched)
            if matched and not first_reason:
                first_reason = f"{rule_type} hit: {type_}"

        if not hits: return False, None
        is_hit = all(hits) if operator == "AND" else any(hits)
        return is_hit, first_reason if is_hit else None

    @staticmethod
    def _numeric_rule_value(rule, *keys, default=0.0):
        for key in keys:
            value = rule.get(key)
            if value not in (None, ""):
                return float(value)
        return float(default)

    @staticmethod
    def _extract_eod_squareoff_time(groups):
        for group in groups or []:
            target_rules = group.get("target_rules", []) or []
            for rule in target_rules:
                if rule.get("eod_squareoff_time"):
                    return rule.get("eod_squareoff_time")
        return None

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
