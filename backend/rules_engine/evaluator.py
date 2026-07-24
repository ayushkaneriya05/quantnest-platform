import json
import logging
import re
from decimal import Decimal

import numpy as np
import pandas as pd

if not hasattr(np, "NaN"):
    np.NaN = np.nan

import pandas_ta as ta
from scipy.stats import norm

from common.enums import (
    ComparisonOperator,
    OperandType,
    LogicalOperator,
    
    
    
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
        close = self._get_price_source(p.get("source", "close"), p)
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
            if indicator_type == OperandType.SMA:
                series = ta.sma(close, length=p["period"])
            elif indicator_type == OperandType.EMA:
                series = ta.ema(close, length=p["period"])
            elif indicator_type == OperandType.WMA:
                series = ta.wma(close, length=p["period"])
            elif indicator_type == OperandType.RSI:
                series = ta.rsi(close, length=p["period"])
            elif indicator_type == OperandType.ROC:
                series = ta.roc(close, length=p["period"])
            elif indicator_type == OperandType.HMA:
                series = ta.hma(close, length=p["period"])
            elif indicator_type == OperandType.ALMA:
                series = ta.alma(close, length=p["period"])
            elif indicator_type == OperandType.KAMA:
                series = ta.kama(close, length=p["period"])
            elif indicator_type == OperandType.DEMA:
                series = ta.dema(close, length=p["period"])
            elif indicator_type == OperandType.TEMA:
                series = ta.tema(close, length=p["period"])
            elif indicator_type == OperandType.MACD:
                macd_df = ta.macd(
                    close,
                    fast=p["fast_period"],
                    slow=p["slow_period"],
                    signal=p["signal_period"],
                )
                if macd_df is not None:
                    # pandas_ta returns columns: MACD_F_S_SIG, MACDh_F_S_SIG, MACDs_F_S_SIG
                    output_line = str(p.get("output_line", "MACD_LINE")).upper()
                    if output_line == "MACD_SIGNAL":
                        cols = [c for c in macd_df.columns if c.startswith("MACDs_")]
                        series = macd_df[cols[0]] if cols else None
                    elif output_line == "MACD_HISTOGRAM":
                        cols = [c for c in macd_df.columns if c.startswith("MACDh_")]
                        series = macd_df[cols[0]] if cols else None
                    else:  # Default to MACD_LINE
                        cols = [c for c in macd_df.columns if c.startswith("MACD_")]
                        series = macd_df[cols[0]] if cols else None
            elif indicator_type == OperandType.BOLLINGER_BANDS:
                bb_df = ta.bbands(close, length=p["period"], std=p["std_dev"])
                if bb_df is not None:
                    output_line = str(p.get("output_line", "UPPER")).upper()
                    if output_line == "LOWER":
                        cols = [c for c in bb_df.columns if c.startswith("BBL_")]
                        series = bb_df[cols[0]] if cols else None
                    elif output_line == "MIDDLE" or output_line == "MID":
                        cols = [c for c in bb_df.columns if c.startswith("BBM_")]
                        series = bb_df[cols[0]] if cols else None
                    else:  # UPPER
                        cols = [c for c in bb_df.columns if c.startswith("BBU_")]
                        series = bb_df[cols[0]] if cols else None
            elif indicator_type == OperandType.VWAP:
                anchor = str(p.get("anchor", "D")).upper()
                series = ta.vwap(high, low, close, volume, anchor=anchor)
            elif indicator_type == OperandType.SUPERTREND:
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
            elif indicator_type in {OperandType.ADX, OperandType.DMI}:
                adx_df = ta.adx(high, low, close, length=p["period"])
                if adx_df is not None:
                    output_line = str(p.get("output_line", "ADX")).upper()
                    if output_line == "PLUS_DI" or output_line == "+DI":
                        cols = [c for c in adx_df.columns if c.startswith("DMP_")]
                        series = adx_df[cols[0]] if cols else None
                    elif output_line == "MINUS_DI" or output_line == "-DI":
                        cols = [c for c in adx_df.columns if c.startswith("DMN_")]
                        series = adx_df[cols[0]] if cols else None
                    else:
                        cols = [c for c in adx_df.columns if c.startswith("ADX_")]
                        series = adx_df[cols[0]] if cols else None
            elif indicator_type == OperandType.STOCHASTIC:
                stoch_df = ta.stoch(
                    high,
                    low,
                    close,
                    k=p["k_period"],
                    d=p["d_period"],
                    smooth_k=p["smooth"],
                )
                if stoch_df is not None:
                    output_line = str(p.get("output_line", "K")).upper()
                    if output_line == "D" or output_line == "%D":
                        cols = [c for c in stoch_df.columns if c.startswith("STOCHd_")]
                        series = stoch_df[cols[0]] if cols else None
                    else:
                        cols = [c for c in stoch_df.columns if c.startswith("STOCHk_")]
                        series = stoch_df[cols[0]] if cols else None
            elif indicator_type == OperandType.ATR:
                series = ta.atr(high, low, close, length=p["period"])
            elif indicator_type == OperandType.CCI:
                series = ta.cci(high, low, close, length=p["period"])
            elif indicator_type == OperandType.WILLIAMS_R:
                series = ta.willr(high, low, close, length=p["period"])
            elif indicator_type == OperandType.OBV:
                series = ta.obv(close, volume)
            elif indicator_type == OperandType.MFI:
                series = ta.mfi(high, low, close, volume, length=p["period"])
            elif indicator_type == OperandType.PIVOT_POINT:
                series = ((high.shift(1) + low.shift(1) + close.shift(1)) / 3).rename("pivot_point")
            elif indicator_type == OperandType.DONCHIAN_CHANNEL:
                dc_df = ta.donchian(high, low, lower_length=p["period"], upper_length=p["period"])
                if dc_df is not None:
                    output_line = str(p.get("output_line", "UPPER")).upper()
                    if output_line == "LOWER":
                        cols = [c for c in dc_df.columns if c.startswith("DCL_")]
                        series = dc_df[cols[0]] if cols else None
                    elif output_line == "MIDDLE" or output_line == "MID":
                        cols = [c for c in dc_df.columns if c.startswith("DCM_")]
                        series = dc_df[cols[0]] if cols else None
                    else:  # UPPER
                        cols = [c for c in dc_df.columns if c.startswith("DCU_")]
                        series = dc_df[cols[0]] if cols else None
            elif indicator_type == OperandType.KELTNER_CHANNEL:
                kc_df = ta.kc(high, low, close, length=p["period"], scalar=p["multiplier"])
                if kc_df is not None:
                    output_line = str(p.get("output_line", "UPPER")).upper()
                    if output_line == "LOWER":
                        cols = [c for c in kc_df.columns if c.startswith("KCLe_")]
                        series = kc_df[cols[0]] if cols else None
                    elif output_line == "MIDDLE" or output_line == "MID":
                        cols = [c for c in kc_df.columns if c.startswith("KCBs_")]
                        series = kc_df[cols[0]] if cols else None
                    else:  # UPPER
                        cols = [c for c in kc_df.columns if c.startswith("KCUe_")]
                        series = kc_df[cols[0]] if cols else None
            elif indicator_type == OperandType.PARABOLIC_SAR:
                af = to_float(p.get("af"), 0.02)
                max_af = to_float(p.get("max_af"), 0.2)
                psar_df = ta.psar(high, low, close, af0=af, af=af, max_af=max_af)
                if psar_df is not None:
                    cols = [c for c in psar_df.columns if c.startswith("PSARl_") or c.startswith("PSARs_") or c.startswith("PSAR_")]
                    series = psar_df[cols[0]] if cols else None
            elif indicator_type == OperandType.ICHIMOKU_CLOUD:
                tenkan = int(p.get("tenkan", 9))
                kijun = int(p.get("kijun", 26))
                senkou = int(p.get("senkou", 52))
                ichimoku_dfs = ta.ichimoku(high, low, close, tenkan=tenkan, kijun=kijun, senkou=senkou)
                if ichimoku_dfs and ichimoku_dfs[0] is not None:
                    df = ichimoku_dfs[0]
                    output_line = str(p.get("output_line", "TENKAN")).upper()
                    if output_line == "KIJUN":
                        cols = [c for c in df.columns if c.startswith("IKS_")]
                        series = df[cols[0]] if cols else None
                    elif output_line == "SENKOU_A":
                        cols = [c for c in df.columns if c.startswith("ISA_")]
                        series = df[cols[0]] if cols else None
                    elif output_line == "SENKOU_B":
                        cols = [c for c in df.columns if c.startswith("ISB_")]
                        series = df[cols[0]] if cols else None
                    elif output_line == "CHIKOU":
                        cols = [c for c in df.columns if c.startswith("ICS_")]
                        series = df[cols[0]] if cols else None
                    else:
                        cols = [c for c in df.columns if c.startswith("ITS_")]
                        series = df[cols[0]] if cols else None
            elif indicator_type == OperandType.CANDLE_PATTERN:
                pattern_enum = str(p.get("pattern", "DOJI")).upper()
                pattern_name = pattern_enum.lower()
                
                # Map specific enums to pandas-ta / TA-Lib expected names
                if "engulfing" in pattern_name:
                    pattern_name = "engulfing"
                elif "harami" in pattern_name:
                    pattern_name = "harami"
                elif pattern_name == "shooting_star":
                    pattern_name = "shootingstar"
                elif pattern_name == "morning_star":
                    pattern_name = "morningstar"
                elif pattern_name == "evening_star":
                    pattern_name = "eveningstar"
                elif pattern_name == "piercing_line":
                    pattern_name = "piercing"
                    
                pattern_df = ta.cdl_pattern(open, high, low, close, name=pattern_name)
                if pattern_df is not None and not pattern_df.empty:
                    cols = pattern_df.columns
                    if cols:
                        raw_series = pattern_df[cols[0]]
                        if pattern_enum in ["ENGULFING_BULLISH", "HARAMI_BULLISH"]:
                            series = raw_series == 100
                        elif pattern_enum in ["ENGULFING_BEARISH", "HARAMI_BEARISH"]:
                            series = raw_series == -100
                        else:
                            series = raw_series != 0
                        
                        # Return as float so it can be compared with boolean (True -> 1.0, False -> 0.0)
                        series = series.astype(float)

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

    def _get_price_source(self, source, params=None):
        source_str = str(source or "close").upper()
        shift_val = int(params.get("source_shift", 0)) if params else 0
        price_series = None

        if source_str in {"OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"}:
            price_series = self.df[source_str.lower()]
        elif source_str == "HL2":
            price_series = (self.df["high"] + self.df["low"]) / 2
        elif source_str == "HLC3":
            price_series = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        elif source_str == "OHLC4":
            price_series = (self.df["open"] + self.df["high"] + self.df["low"] + self.df["close"]) / 4
        elif source_str == "CURRENT_DAY_OPEN":
            price_series = self.df["open"].resample("1d").first().reindex(self.df.index, method="ffill")
        elif source_str == "PREV_WEEK_HIGH":
            price_series = self.df["high"].resample("W").max().shift(1).reindex(self.df.index, method="ffill")
        elif source_str == "PREV_WEEK_LOW":
            price_series = self.df["low"].resample("W").min().shift(1).reindex(self.df.index, method="ffill")

        if price_series is not None:
            if shift_val > 0:
                price_series = price_series.shift(shift_val)
            return price_series
            
        # Indicator Chaining: If source is an OperandType, evaluate it recursively
        try:
            op_type = OperandType(source_str)
            source_params = params.get("source_params", {}) if params else {}
            series = self.get_series(op_type, source_params)
            if series is not None and not series.isna().all():
                return series
        except ValueError:
            pass

        logger.warning("Unsupported price source '%s', defaulting to close", source_str)
        return self.df["close"]


class RuleEvaluator:
    """
    Evaluates trading rules against historical candle data.
    Supports both Django model instances and dict snapshots from backtests.
    """

    def __init__(self, bars_df, candle_completion_rule="ON_CLOSE", mtf_data=None, indicator_engine=None, mtf_indicator_engines=None, instrument=None):
        self.df = bars_df.copy()
        self.instrument = instrument
        self.candle_completion_rule = candle_completion_rule
        self.mtf_data = mtf_data or {} # Dict of {timeframe: df}
        self.indicator_engine = indicator_engine if indicator_engine is not None else IndicatorEngine(self.df)
        self.mtf_indicator_engines = mtf_indicator_engines if mtf_indicator_engines is not None else {}

    def evaluate_group(self, group, state=None):
        """
        Evaluate a RuleGroup and return a boolean series.
        """
        rules = self._get_group_rules(group)
        if not rules:
            logger.warning("Rule group %s has no active rules; treating it as no signal", get_any_field(group, "name", "unnamed"))
            return self._false_series()

        results = []
        for rule in rules:
            res = self.evaluate_rule(rule, state)
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


    def evaluate_rule(self, rule, state=None):
        """
        Evaluates a single rule (Unified Architecture) against the cached dataframe.
        Returns a boolean Series.
        """
        try:
            op_a_type = get_any_field(rule, "operand_a_type")
            op_a_params = get_any_field(rule, "operand_a_params", {}) or {}
            
            if not op_a_type:
                return self._false_series()
                

            op_a_timeframe = get_any_field(rule, "operand_a_timeframe")
            val_a = self._resolve_operand(op_a_type, op_a_params, state, timeframe=op_a_timeframe)
            
            op_b_type = get_any_field(rule, "operand_b_type")
            op_b_params = get_any_field(rule, "operand_b_params", {}) or {}
            op_b_timeframe = get_any_field(rule, "operand_b_timeframe")
            val_b = self._resolve_operand(op_b_type, op_b_params, state, timeframe=op_b_timeframe)
            
            comparison = get_any_field(rule, "comparison", ComparisonOperator.EQUAL)
            
            if isinstance(val_a, pd.Series) and val_a.dtype == bool:
                if not op_b_type:
                    return val_a
                    
            return self._compare(val_a, comparison, val_b)
        except Exception as e:
            logger.error("Error evaluating rule %s: %s", getattr(rule, "id", "Unknown"), str(e))
            return self._false_series()

    def _resolve_operand(self, op_type, params, state=None, timeframe=None):
        if not op_type:
            return 0.0
            
        target_df = self.df
        target_engine = self.indicator_engine
        if timeframe and timeframe in self.mtf_data and timeframe in self.mtf_indicator_engines:
            target_df = self.mtf_data[timeframe]
            target_engine = self.mtf_indicator_engines[timeframe]
            
        if op_type == OperandType.CONSTANT:
            return to_float(params.get("value"), 0.0)
            
        if op_type == OperandType.MATH_EXPRESSION:
            return self._evaluate_custom_expression(params, state)
            
        if state is not None:
            # State-based properties
            if op_type == OperandType.POSITION_PNL_PERCENTAGE:
                return float(state.get("pnl_percentage", 0.0))
            if op_type == OperandType.POSITION_PNL_POINTS:
                return float(state.get("pnl_points", 0.0))
            if op_type == OperandType.ENTRY_PRICE:
                return float(state.get("avg_price", 0.0))
            if op_type == OperandType.TRAILING_PEAK_OFFSET:
                return float(state.get("peak_price", 0.0)) - float(self.df["close"].iloc[-1])
            if op_type == OperandType.TIME_DECAY:
                return float(state.get("bars_held", 0.0))

            
        shift_val = int(params.get("shift", 0)) if params else 0
        price_series = None

        if op_type == OperandType.LTP or op_type == OperandType.CLOSE:
            price_series = target_df["close"]
        elif op_type == OperandType.OPEN:
            price_series = target_df["open"]
        elif op_type == OperandType.HIGH:
            price_series = target_df["high"]
        elif op_type == OperandType.LOW:
            price_series = target_df["low"]
        elif op_type == OperandType.VOLUME:
            price_series = target_df["volume"]
        elif op_type == OperandType.HL2:
            price_series = (target_df["high"] + target_df["low"]) / 2
        elif op_type == OperandType.HLC3:
            price_series = (target_df["high"] + target_df["low"] + target_df["close"]) / 3
        elif op_type == OperandType.OHLC4:
            price_series = (target_df["open"] + target_df["high"] + target_df["low"] + target_df["close"]) / 4
        elif op_type == OperandType.CURRENT_DAY_OPEN:
            daily_open = target_df["open"].resample("1d").first()
            price_series = daily_open.reindex(target_df.index, method="ffill")
        elif op_type == OperandType.PREV_WEEK_HIGH:
            weekly_high = target_df["high"].resample("W").max().shift(1)
            price_series = weekly_high.reindex(target_df.index, method="ffill")
        elif op_type == OperandType.PREV_WEEK_LOW:
            weekly_low = target_df["low"].resample("W").min().shift(1)
            price_series = weekly_low.reindex(target_df.index, method="ffill")
        elif op_type == OperandType.CANDLE_BODY_SIZE:
            mode = params.get("mode", "POINTS")
            body_size = (target_df["close"] - target_df["open"]).abs()
            if mode == "PERCENTAGE":
                price_series = (body_size / target_df["open"]) * 100
            else:
                price_series = body_size

        if price_series is not None:
            if shift_val > 0:
                price_series = price_series.shift(shift_val)
            return price_series
        # Indicator Types
        indicator_types = {
            OperandType.SMA, OperandType.EMA, OperandType.WMA, OperandType.HMA, OperandType.ALMA, OperandType.KAMA, OperandType.DEMA, OperandType.TEMA,
            OperandType.RSI, OperandType.ROC, OperandType.MACD, OperandType.BOLLINGER_BANDS, OperandType.SUPERTREND, OperandType.ADX, OperandType.DMI, OperandType.STOCHASTIC, OperandType.ATR,
            OperandType.CCI, OperandType.WILLIAMS_R, OperandType.OBV, OperandType.MFI, OperandType.PIVOT_POINT, OperandType.KELTNER_CHANNEL, OperandType.DONCHIAN_CHANNEL, OperandType.PARABOLIC_SAR, OperandType.ICHIMOKU_CLOUD,
            OperandType.VWAP, OperandType.CANDLE_PATTERN
        }
        if op_type in indicator_types:
            series = target_engine.get_series(op_type, params)
            if series is not None and shift_val > 0:
                series = series.shift(shift_val)
            return series

        logger.warning("Unsupported op_type: %s", op_type)

        # If it's something else we don't know, return 0.0
        return 0.0

    def _compare(self, value_1, operator, value_2):
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
        else:
            logger.warning("Unsupported comparison operator: %s", operator)
            result = self._false_series()

        return self._normalize_boolean_series(result)

    def _evaluate_custom_expression(self, params, state=None):
        expression = str(params.get("expression") or "").strip()
        if not expression:
            logger.warning("Custom rule missing expression")
            return self._false_series()

        variables = params.get("variables") or {}
        if not self._is_safe_custom_expression(expression, variables=variables):
            logger.warning("Rejected unsafe custom rule expression: %s", expression)
            return self._false_series()

        variables = params.get("variables") or {}
        eval_df = self.df.copy()
        
        # Calculate and inject dynamic variables into the dataframe
        try:
            for var_name, var_config in variables.items():
                if not isinstance(var_config, dict):
                    continue
                var_type = var_config.get("type")
                var_params = var_config.get("params", {})
                var_timeframe = var_config.get("timeframe")
                
                # We can pass state and timeframe to _resolve_operand.
                series = self._resolve_operand(var_type, var_params, state=state, timeframe=var_timeframe)
                
                if isinstance(series, pd.Series) and len(series) != len(eval_df):
                    series = series.reindex(eval_df.index, method="ffill")
                    
                eval_df[var_name] = series
        except Exception as e:
            logger.warning("Failed to evaluate nested variables for math expression: %s", e)
            return self._false_series()

        try:
            result = eval_df.eval(expression, engine="numexpr")
        except Exception as exc:
            try:
                result = eval_df.eval(expression, engine="python")
            except Exception:
                logger.warning("Custom rule expression failed '%s': %s", expression, exc)
                return self._false_series()

        return self._normalize_boolean_series(result)

    @staticmethod
    def _is_safe_custom_expression(expression, variables=None):
        if "__" in expression or "@" in expression:
            return False
        allowed_columns = {"open", "high", "low", "close", "volume"}
        if variables:
            allowed_columns.update(variables.keys())
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expression))
        if not tokens.issubset(allowed_columns):
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9_\s\.\<\>\=\!\&\|\(\)\+\-\*\/\%]+", expression))

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
