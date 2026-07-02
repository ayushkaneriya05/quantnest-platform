import json
import logging
import re
from decimal import Decimal

import numpy as np
import pandas as pd

if not hasattr(np, "NaN"):
    np.NaN = np.nan

import pandas_ta as ta

from common.enums import (
    ComparisonOperator,
    IndicatorType,
    LogicalOperator,
    PriceActionType,
    RuleCategory,
    VolumeConditionType,
    CandleCompletionRule,
)
from common.trading_utils import get_any_field, to_float

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """
    Computes technical indicators using pandas_ta and caches them.
    Abstracted from RuleEvaluator to adhere to single responsibility principle.
    """
    def __init__(self, df):
        self.df = df
        self._indicators_cached = {}

    def get_series(self, indicator_type, params):
        normalized_params = self._normalize_params(params)
        cache_key = f"{indicator_type}:{json.dumps(normalized_params, sort_keys=True, default=str)}"
        if cache_key in self._indicators_cached:
            return self._indicators_cached[cache_key]

        p = normalized_params
        close = self._get_price_source(p.get("source", "close"))
        high = self.df["high"]
        low = self.df["low"]
        volume = self.df["volume"]
        series = None

        # Warm-up guard: emit a warning when there are fewer bars than the
        # primary indicator period.  The indicator will still be computed
        # (pandas_ta fills the warm-up rows with NaN which the evaluator
        # treats as False), but the warning helps users diagnose silent
        # non-signals at session start.
        required_bars = max(
            int(p.get("period", 1)),
            int(p.get("slow_period", 1)),
        )
        if len(self.df) < required_bars:
            logger.warning(
                "Indicator %s requires %d bars but only %d are available — "
                "signals will be suppressed until enough history loads.",
                indicator_type, required_bars, len(self.df),
            )

        try:
            if indicator_type == IndicatorType.SMA:
                series = ta.sma(close, length=p["period"])
            elif indicator_type == IndicatorType.EMA:
                series = ta.ema(close, length=p["period"])
            elif indicator_type == IndicatorType.WMA:
                series = ta.wma(close, length=p["period"])
            elif indicator_type == IndicatorType.RSI:
                series = ta.rsi(close, length=p["period"])
            elif indicator_type in {
                IndicatorType.MACD,
                IndicatorType.MACD_SIGNAL,
                IndicatorType.MACD_HISTOGRAM,
            }:
                macd_df = ta.macd(
                    close,
                    fast=p["fast_period"],
                    slow=p["slow_period"],
                    signal=p["signal_period"],
                )
                if macd_df is not None:
                    # pandas_ta returns columns: MACD_F_S_SIG, MACDh_F_S_SIG, MACDs_F_S_SIG
                    # Use named filtering — robust to column-order changes across versions.
                    if indicator_type == IndicatorType.MACD:
                        cols = [c for c in macd_df.columns if c.startswith("MACD_")]
                        series = macd_df[cols[0]] if cols else None
                    elif indicator_type == IndicatorType.MACD_SIGNAL:
                        cols = [c for c in macd_df.columns if c.startswith("MACDs_")]
                        series = macd_df[cols[0]] if cols else None
                    else:  # MACD_HISTOGRAM
                        cols = [c for c in macd_df.columns if c.startswith("MACDh_")]
                        series = macd_df[cols[0]] if cols else None
            elif indicator_type in {
                IndicatorType.BOLLINGER_UPPER,
                IndicatorType.BOLLINGER_MID,
                IndicatorType.BOLLINGER_LOWER,
            }:
                bb_df = ta.bbands(close, length=p["period"], std=p["std_dev"])
                if bb_df is not None:
                    # pandas_ta columns: BBL_P_S, BBM_P_S, BBU_P_S, BBB_P_S, BBP_P_S
                    # Use named prefix filtering.
                    if indicator_type == IndicatorType.BOLLINGER_LOWER:
                        cols = [c for c in bb_df.columns if c.startswith("BBL_")]
                        series = bb_df[cols[0]] if cols else None
                    elif indicator_type == IndicatorType.BOLLINGER_MID:
                        cols = [c for c in bb_df.columns if c.startswith("BBM_")]
                        series = bb_df[cols[0]] if cols else None
                    else:  # BOLLINGER_UPPER
                        cols = [c for c in bb_df.columns if c.startswith("BBU_")]
                        series = bb_df[cols[0]] if cols else None
            elif indicator_type == IndicatorType.VWAP:
                series = ta.vwap(high, low, close, volume)
            elif indicator_type == IndicatorType.SUPERTREND:
                supertrend_df = ta.supertrend(
                    high,
                    low,
                    close,
                    length=p["period"],
                    multiplier=p["multiplier"],
                )
                if supertrend_df is not None:
                    # Column: SUPERT_P_M (the actual supertrend line)
                    cols = [c for c in supertrend_df.columns if c.startswith("SUPERT_") and "d" not in c.lower()]
                    series = supertrend_df[cols[0]] if cols else supertrend_df.iloc[:, 0]
            elif indicator_type in {IndicatorType.ADX, IndicatorType.PLUS_DI, IndicatorType.MINUS_DI}:
                adx_df = ta.adx(high, low, close, length=p["period"])
                if adx_df is not None:
                    # pandas_ta columns: ADX_P, DMP_P, DMN_P
                    if indicator_type == IndicatorType.ADX:
                        cols = [c for c in adx_df.columns if c.startswith("ADX_")]
                        series = adx_df[cols[0]] if cols else None
                    elif indicator_type == IndicatorType.PLUS_DI:
                        cols = [c for c in adx_df.columns if c.startswith("DMP_")]
                        series = adx_df[cols[0]] if cols else None
                    else:  # MINUS_DI
                        cols = [c for c in adx_df.columns if c.startswith("DMN_")]
                        series = adx_df[cols[0]] if cols else None
            elif indicator_type in {IndicatorType.STOCHASTIC_K, IndicatorType.STOCHASTIC_D}:
                stoch_df = ta.stoch(
                    high,
                    low,
                    close,
                    k=p["k_period"],
                    d=p["d_period"],
                    smooth_k=p["smooth"],
                )
                if stoch_df is not None:
                    # pandas_ta columns: STOCHk_K_D_S, STOCHd_K_D_S
                    if indicator_type == IndicatorType.STOCHASTIC_K:
                        cols = [c for c in stoch_df.columns if c.startswith("STOCHk_")]
                        series = stoch_df[cols[0]] if cols else None
                    else:
                        cols = [c for c in stoch_df.columns if c.startswith("STOCHd_")]
                        series = stoch_df[cols[0]] if cols else None
            elif indicator_type == IndicatorType.ATR:
                series = ta.atr(high, low, close, length=p["period"])
            elif indicator_type == IndicatorType.CCI:
                series = ta.cci(high, low, close, length=p["period"])
            elif indicator_type == IndicatorType.WILLIAMS_R:
                series = ta.willr(high, low, close, length=p["period"])
            elif indicator_type == IndicatorType.OBV:
                series = ta.obv(close, volume)
            elif indicator_type == IndicatorType.MFI:
                series = ta.mfi(high, low, close, volume, length=p["period"])
            elif indicator_type == IndicatorType.PIVOT_POINT:
                series = ((high.shift(1) + low.shift(1) + close.shift(1)) / 3).rename("pivot_point")
        except Exception as exc:
            logger.exception("Error calculating indicator %s: %s", indicator_type, exc)
            series = None

        if series is None:
            logger.warning("Unsupported or failed indicator: %s — returning NaN series", indicator_type)
            # Return NaN so comparisons produce False rather than
            # misleading zeros (zero could be a valid price/level).
            series = pd.Series(float("nan"), index=self.df.index, dtype="float64")

        series = pd.Series(series, index=self.df.index, dtype="float64")
        self._indicators_cached[cache_key] = series
        return series

    def _normalize_params(self, params):
        params = dict(params or {})
        normalized = dict(params)

        alias_map = {
            "length": "period",
            "fast": "fast_period",
            "slow": "slow_period",
            "signal": "signal_period",
            "std": "std_dev",
            "k": "k_period",
            "d": "d_period",
            "smooth_k": "smooth",
        }

        for old_key, new_key in alias_map.items():
            if old_key in normalized and new_key not in normalized:
                normalized[new_key] = normalized[old_key]

        normalized.setdefault("period", 14)
        normalized.setdefault("fast_period", 12)
        normalized.setdefault("slow_period", 26)
        normalized.setdefault("signal_period", 9)
        normalized.setdefault("std_dev", 2)
        normalized.setdefault("k_period", 14)
        normalized.setdefault("d_period", 3)
        normalized.setdefault("smooth", 3)
        normalized.setdefault("multiplier", 3)
        normalized.setdefault("source", "close")
        normalized.setdefault("lookback", normalized.get("period", 20))
        return normalized

    def _get_price_source(self, source):
        source = str(source or "close").lower()
        if source in self.df.columns:
            return self.df[source]
        if source == "hl2":
            return (self.df["high"] + self.df["low"]) / 2
        if source == "hlc3":
            return (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        if source == "ohlc4":
            return (self.df["open"] + self.df["high"] + self.df["low"] + self.df["close"]) / 4
        logger.warning("Unsupported price source '%s', defaulting to close", source)
        return self.df["close"]


class RuleEvaluator:
    """
    Evaluates trading rules against historical candle data.
    Supports both Django model instances and dict snapshots from backtests.
    """

    def __init__(self, bars_df, candle_completion_rule="ON_CLOSE", mtf_data=None, indicator_engine=None, mtf_indicator_engines=None):
        self.df = bars_df.copy()
        self.candle_completion_rule = candle_completion_rule
        self.mtf_data = mtf_data or {} # Dict of {timeframe: df}
        self.indicator_engine = indicator_engine if indicator_engine is not None else IndicatorEngine(self.df)
        self.mtf_indicator_engines = mtf_indicator_engines if mtf_indicator_engines is not None else {}

    def evaluate_group(self, group):
        """
        Evaluate a RuleGroup and return a boolean series.
        """
        rules = self._get_group_rules(group)
        if not rules:
            logger.warning("Rule group %s has no active rules; treating it as no signal", get_any_field(group, "name", "unnamed"))
            return self._false_series()

        results = []
        for rule in rules:
            res = self.evaluate_rule(rule)
            # If MTF, we might need to re-index the result back to base dataframe index
            if len(res) != len(self.df):
                res = res.reindex(self.df.index, method="ffill").fillna(False)
            results.append(res)

        if not results:
            return self._false_series()

        logical_operator = get_any_field(group, "logical_operator", LogicalOperator.AND)
        combined = results[0]

        for result in results[1:]:
            if logical_operator == LogicalOperator.OR:
                combined = combined | result
            else:
                combined = combined & result

        return self._normalize_boolean_series(combined)

    def evaluate_rule(self, rule):
        """
        Evaluate a single Rule and return a boolean series.
        """
        category = get_any_field(rule, "category")
        indicator_type = get_any_field(rule, "indicator_type")
        price_action_type = get_any_field(rule, "price_action_type")
        volume_condition_type = get_any_field(rule, "volume_condition_type")
        tf_override = get_any_field(rule, "timeframe_override")

        # Handle MTF context switch
        original_engine = self.indicator_engine
        original_df = self.df
        
        if tf_override and tf_override in self.mtf_data:
            override_df = self.mtf_data[tf_override]
            self.df = override_df
            if tf_override in self.mtf_indicator_engines:
                self.indicator_engine = self.mtf_indicator_engines[tf_override]
            else:
                self.indicator_engine = IndicatorEngine(override_df)
        
        try:
            if category == RuleCategory.INDICATOR or indicator_type:
                res = self._evaluate_indicator_rule(rule)
            elif category == RuleCategory.PRICE_ACTION or price_action_type:
                res = self._evaluate_price_action_rule(rule)
            elif category == RuleCategory.VOLUME or volume_condition_type:
                res = self._evaluate_volume_rule(rule)
            elif category == RuleCategory.CUSTOM:
                res = self._evaluate_custom_rule(rule)
            else:
                res = self._false_series()
        finally:
            # Restore original context
            self.indicator_engine = original_engine
            self.df = original_df

        return res


    def _evaluate_indicator_rule(self, rule):
        indicator_type = get_any_field(rule, "indicator_type")
        if not indicator_type:
            return self._false_series()

        params = get_any_field(rule, "params", {}) or {}
        value_1 = self.indicator_engine.get_series(indicator_type, params)
        comparison = get_any_field(rule, "comparison", ComparisonOperator.GREATER)
        compare_to_indicator = get_any_field(rule, "compare_to_indicator")

        if compare_to_indicator:
            value_2 = self.indicator_engine.get_series(
                compare_to_indicator,
                get_any_field(rule, "compare_to_params", {}) or {},
            )
        else:
            value_2 = to_float(get_any_field(rule, "value"), 0.0)

        value_3 = to_float(get_any_field(rule, "value2"), 0.0)

        # For REAL_TIME evaluation we should still compare the computed
        # indicator series against the configured threshold or comparison
        # series. Do not override the value_1 series with raw candle highs/lows,
        # because that changes rule semantics and creates mismatches between
        # backtest and live execution.
        return self._compare(value_1, comparison, value_2, value_3)



    def _compare(self, value_1, operator, value_2, value_3=None):
        """
        Perform comparison between two series or a series and a scalar.
        """
        if operator == ComparisonOperator.GREATER:
            result = value_1 > value_2
        elif operator == ComparisonOperator.LESS:
            result = value_1 < value_2
        elif operator == ComparisonOperator.GREATER_EQUAL:
            result = value_1 >= value_2
        elif operator == ComparisonOperator.LESS_EQUAL:
            result = value_1 <= value_2
        elif operator == ComparisonOperator.EQUAL:
            result = value_1 == value_2
        elif operator == ComparisonOperator.CROSSES_ABOVE:
            previous_2 = value_2.shift(1) if isinstance(value_2, pd.Series) else value_2
            result = (value_1 > value_2) & (value_1.shift(1) <= previous_2)
        elif operator == ComparisonOperator.CROSSES_BELOW:
            previous_2 = value_2.shift(1) if isinstance(value_2, pd.Series) else value_2
            result = (value_1 < value_2) & (value_1.shift(1) >= previous_2)
        elif operator == ComparisonOperator.BETWEEN:
            # Handle both scalar and Series values for BETWEEN comparisons
            if isinstance(value_2, pd.Series):
                # Two-indicator BETWEEN: value_2 <= value_1 <= value_3 (Series)
                lower = value_2
                upper = value_3 if isinstance(value_3, pd.Series) else pd.Series(to_float(value_3, 0.0), index=self.df.index)
                result = (value_1 >= lower) & (value_1 <= upper)
            else:
                lower = min(to_float(value_2, 0.0), to_float(value_3, 0.0))
                upper = max(to_float(value_2, 0.0), to_float(value_3, 0.0))
                result = value_1.between(lower, upper, inclusive="both")
        else:
            logger.warning("Unsupported comparison operator: %s", operator)
            result = self._false_series()

        return self._normalize_boolean_series(result)

    def _evaluate_custom_rule(self, rule):
        params = get_any_field(rule, "params", {}) or {}
        expression = str(params.get("expression") or "").strip()
        if not expression:
            logger.warning("Custom rule missing expression: %s", rule)
            return self._false_series()

        if not self._is_safe_custom_expression(expression):
            logger.warning("Rejected unsafe custom rule expression: %s", expression)
            return self._false_series()

        try:
            result = self.df.eval(expression, engine="numexpr")
        except Exception as exc:
            try:
                result = self.df.eval(expression, engine="python")
            except Exception:
                logger.warning("Custom rule expression failed '%s': %s", expression, exc)
                return self._false_series()

        return self._normalize_boolean_series(result)

    @staticmethod
    def _is_safe_custom_expression(expression):
        if "__" in expression or "@" in expression:
            return False
        allowed_columns = {"open", "high", "low", "close", "volume"}
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expression))
        if not tokens.issubset(allowed_columns):
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9_\s\.\<\>\=\!\&\|\(\)\+\-\*\/\%]+", expression))

    def _evaluate_price_action_rule(self, rule):
        price_action_type = get_any_field(rule, "price_action_type")
        params = self._normalize_params(get_any_field(rule, "params", {}) or {})
        df = self.df
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        lookback = max(int(params.get("lookback", params.get("period", 20))), 1)
        breakout_source = str(params.get("breakout_source", "close")).lower()
        breakout_series = self._get_breakout_series(breakout_source)
        rolling_high = high.shift(1).rolling(window=lookback, min_periods=1).max()
        rolling_low = low.shift(1).rolling(window=lookback, min_periods=1).min()

        if price_action_type == PriceActionType.DOJI:
            result = ta.cdl_doji(open_, high, low, close) != 0
        elif price_action_type == PriceActionType.HAMMER:
            result = ta.cdl_hammer(open_, high, low, close) > 0
        elif price_action_type == PriceActionType.SHOOTING_STAR:
            result = ta.cdl_shootingstar(open_, high, low, close) < 0
        elif price_action_type == PriceActionType.MORNING_STAR:
            result = ta.cdl_morningstar(open_, high, low, close) > 0
        elif price_action_type == PriceActionType.EVENING_STAR:
            result = ta.cdl_eveningstar(open_, high, low, close) < 0
        elif price_action_type == PriceActionType.ENGULFING_BULLISH:
            result = ta.cdl_engulfing(open_, high, low, close) > 0
        elif price_action_type == PriceActionType.ENGULFING_BEARISH:
            result = ta.cdl_engulfing(open_, high, low, close) < 0
        elif price_action_type == PriceActionType.INSIDE_CANDLE:
            result = (high < high.shift(1)) & (low > low.shift(1))
        elif price_action_type == PriceActionType.OUTSIDE_CANDLE:
            result = (high > high.shift(1)) & (low < low.shift(1))
        elif price_action_type == PriceActionType.HIGHER_HIGH:
            result = high > high.shift(1)
        elif price_action_type == PriceActionType.HIGHER_LOW:
            result = low > low.shift(1)
        elif price_action_type == PriceActionType.LOWER_HIGH:
            result = high < high.shift(1)
        elif price_action_type == PriceActionType.LOWER_LOW:
            result = low < low.shift(1)
        elif price_action_type == PriceActionType.GAP_UP:
            result = open_ > high.shift(1)
        elif price_action_type == PriceActionType.GAP_DOWN:
            result = open_ < low.shift(1)
        elif price_action_type == PriceActionType.BREAKOUT_HIGH:
            result = breakout_series > rolling_high
        elif price_action_type == PriceActionType.BREAKDOWN_LOW:
            result = breakout_series < rolling_low
        elif price_action_type == PriceActionType.SUPPORT_BREAKOUT:
            result = (breakout_series > rolling_low) & (breakout_series.shift(1) <= rolling_low.shift(1))
        elif price_action_type == PriceActionType.RESISTANCE_BREAKOUT:
            result = (breakout_series > rolling_high) & (breakout_series.shift(1) <= rolling_high.shift(1))
        elif price_action_type == PriceActionType.RANGE_BREAKOUT:
            result = (breakout_series > rolling_high) | (breakout_series < rolling_low)
        elif price_action_type == PriceActionType.PREV_DAY_HIGH:
            prev_day_high = high.resample("1D").max().shift(1).reindex(df.index, method="ffill")
            result = breakout_series > prev_day_high
        elif price_action_type == PriceActionType.PREV_DAY_LOW:
            prev_day_low = low.resample("1D").min().shift(1).reindex(df.index, method="ffill")
            result = breakout_series < prev_day_low
        else:
            logger.warning("Unsupported price action type: %s", price_action_type)
            result = self._false_series()

        return self._normalize_boolean_series(result)

    def _evaluate_volume_rule(self, rule):
        volume_condition_type = get_any_field(rule, "volume_condition_type")
        params = self._normalize_params(get_any_field(rule, "params", {}) or {})
        volume = self.df["volume"]
        close = self.df["close"]
        period = max(int(params.get("period", 20)), 1)

        if volume_condition_type == VolumeConditionType.VOLUME_ABOVE_AVG:
            avg_volume = ta.sma(volume, length=period)
            result = volume > avg_volume
        elif volume_condition_type == VolumeConditionType.VOLUME_SPIKE:
            avg_volume = ta.sma(volume, length=period)
            multiplier = to_float(params.get("multiplier"), 2.0)
            result = volume > (avg_volume * multiplier)
        elif volume_condition_type == VolumeConditionType.VOLUME_DIVERGENCE:
            price_change = close.diff(periods=period)
            volume_change = volume.diff(periods=period)
            direction = str(params.get("direction", "ANY")).upper()

            if direction == "BULLISH":
                result = (price_change < 0) & (volume_change > 0)
            elif direction == "BEARISH":
                result = (price_change > 0) & (volume_change < 0)
            else:
                result = ((price_change > 0) & (volume_change < 0)) | ((price_change < 0) & (volume_change > 0))
        else:
            logger.warning("Unsupported volume condition type: %s", volume_condition_type)
            result = self._false_series()

        return self._normalize_boolean_series(result)

    def _get_group_rules(self, group):
        rules = get_any_field(group, "rules", [])

        if hasattr(rules, "filter"):
            rules = rules.filter(is_active=True)
        else:
            rules = [rule for rule in list(rules or []) if get_any_field(rule, "is_active", True)]

        return list(rules)

    def _normalize_params(self, params):
        """Delegate to IndicatorEngine for consistent parameter normalization."""
        return self.indicator_engine._normalize_params(params)

    def _get_breakout_series(self, breakout_source):
        if breakout_source in {"high", "low", "open", "close"}:
            return self.df[breakout_source]
        return self.df["close"]

    def _normalize_boolean_series(self, series):
        return pd.Series(series, index=self.df.index).fillna(False).astype(bool)

    def _true_series(self):
        return pd.Series(True, index=self.df.index, dtype=bool)

    def _false_series(self):
        return pd.Series(False, index=self.df.index, dtype=bool)
