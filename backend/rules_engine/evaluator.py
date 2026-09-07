import json
import logging
import re
import numpy as np
import pandas as pd

if not hasattr(np, "NaN"):
    np.NaN = np.nan

import pandas_ta as ta
from common.enums import (
    ComparisonOperator,
    OperandType,
    LogicalOperator
)
from common.trading_utils import get_any_field, to_float
from .indicators import IndicatorEngine, INDICATOR_OPERANDS
from .math_utils import fast_ffill_align_float, fast_ffill_align_bool, _fast_crosses_above, _fast_crosses_below

logger = logging.getLogger(__name__)




class RuleEvaluator:
    """
    Evaluates trading rules against historical candle data.
    Supports both Django model instances and dict snapshots from backtests.
    """

    def __init__(self, bars_df, mtf_data=None, indicator_engine=None, mtf_indicator_engines=None, instrument=None):
        self.df = bars_df.copy()
        self.instrument = instrument
        self.mtf_data = mtf_data or {} # Dict of {timeframe: df}
        self.indicator_engine = indicator_engine if indicator_engine is not None else IndicatorEngine(self.df)
        self.mtf_indicator_engines = mtf_indicator_engines if mtf_indicator_engines is not None else {}
        
        # Initialize evaluation statistics
        self.evaluation_stats = {
            'total_evaluations': 0,
            'failed_evaluations': 0,
            'success_rate': 0.0
        }

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
            # If MTF, use O(1) Numpy forward-fill alignment
            if len(res) != len(self.df):
                aligned_vals = fast_ffill_align_bool(res.index.values.astype(np.int64), res.values, self.df.index.values.astype(np.int64))
                res = pd.Series(aligned_vals, index=self.df.index)
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
        self.evaluation_stats['total_evaluations'] += 1
        try:
            op_a_type = get_any_field(rule, "operand_a_type")
            op_a_params = get_any_field(rule, "operand_a_params", {}) or {}
            
            if not op_a_type:
                return self._false_series()
            
            # Validate indicator parameters
            self._validate_indicator_params(op_a_type, op_a_params)
                
            op_a_timeframe = get_any_field(rule, "operand_a_timeframe")
            val_a = self._resolve_operand(op_a_type, op_a_params, state, timeframe=op_a_timeframe)
            
            op_b_type = get_any_field(rule, "operand_b_type")
            op_b_params = get_any_field(rule, "operand_b_params", {}) or {}
            op_b_timeframe = get_any_field(rule, "operand_b_timeframe")
            
            # Validate indicator parameters for operand B
            if op_b_type:
                self._validate_indicator_params(op_b_type, op_b_params)
            
            val_b = self._resolve_operand(op_b_type, op_b_params, state, timeframe=op_b_timeframe)
            
            comparison = get_any_field(rule, "comparison", ComparisonOperator.EQUAL)
            
            # Validate comparison operator
            self._validate_comparison(val_a, comparison, val_b)
            
            if isinstance(val_a, pd.Series) and val_a.dtype == bool:
                if not op_b_type:
                    return val_a
                    
            return self._compare(val_a, comparison, val_b)
        except (ValueError, TypeError) as e:
            # Parameter or validation errors - critical
            self.evaluation_stats['failed_evaluations'] += 1
            self._update_success_rate()
            logger.error("Validation error evaluating rule %s: %s", getattr(rule, "id", "Unknown"), str(e))
            return self._false_series()
        except Exception as e:
            # Other errors - log but continue
            self.evaluation_stats['failed_evaluations'] += 1
            self._update_success_rate()
            logger.error("Error evaluating rule %s: %s", getattr(rule, "id", "Unknown"), str(e))
            return self._false_series()
    
    def _validate_indicator_params(self, indicator_type, params):
        """Validate indicator parameters."""
        if not params:
            return
            
        from common.enums import OperandType
        
        if indicator_type in [OperandType.SMA, OperandType.EMA, OperandType.RSI]:
            if params.get("period", 0) <= 0:
                raise ValueError(f"{indicator_type} requires positive period")
        elif indicator_type == OperandType.MACD:
            if params.get("fast_period", 0) <= 0 or params.get("slow_period", 0) <= 0:
                raise ValueError("MACD requires positive fast and slow periods")
            if params.get("fast_period", 0) >= params.get("slow_period", 0):
                raise ValueError("MACD fast_period must be less than slow_period")
        elif indicator_type == OperandType.BOLLINGER_BANDS:
            if params.get("period", 0) <= 0:
                raise ValueError("Bollinger Bands requires positive period")
            if params.get("std_dev", 0) <= 0:
                raise ValueError("Bollinger Bands requires positive std_dev")
        elif indicator_type == OperandType.ATR:
            if params.get("period", 0) <= 0:
                raise ValueError("ATR requires positive period")
    
    def _validate_comparison(self, val_a, operator, val_b):
        """Validate comparison operator is appropriate for operand types."""
        from common.enums import ComparisonOperator
        
        if operator in [ComparisonOperator.CROSSES_ABOVE, ComparisonOperator.CROSSES_BELOW]:
            if not isinstance(val_a, pd.Series):
                raise ValueError("Crosses operators require series operands")
            if not isinstance(val_b, (pd.Series, (int, float))):
                raise ValueError("Crosses operators require series or scalar comparison")
    
    def _update_success_rate(self):
        """Update evaluation success rate."""
        total = self.evaluation_stats['total_evaluations']
        if total > 0:
            self.evaluation_stats['success_rate'] = (
                (total - self.evaluation_stats['failed_evaluations']) / total
            )


    def _resolve_operand(self, op_type, params, state=None, timeframe=None):
        if not op_type:
            return self._nan_series()
            
        target_df = self.df
        target_engine = self.indicator_engine
        if timeframe and timeframe in self.mtf_data:
            target_df = self.mtf_data[timeframe]
            if timeframe in self.mtf_indicator_engines:
                target_engine = self.mtf_indicator_engines[timeframe]
            else:
                target_engine = IndicatorEngine(target_df)
                self.mtf_indicator_engines[timeframe] = target_engine
            
        if op_type == OperandType.CONSTANT:
            return to_float(params.get("value"), 0.0)
            
        if op_type == OperandType.MATH_EXPRESSION:
            return self._evaluate_custom_expression(params, state, target_df=target_df)
            
        if state is not None:
            # State-based properties
            if op_type == OperandType.POSITION_PNL_PERCENTAGE:
                return self._state_pnl_percentage(state)
            if op_type == OperandType.POSITION_PNL_POINTS:
                return self._state_pnl_points(state)
            if op_type == OperandType.ENTRY_PRICE:
                return float(state.get("avg_price", 0.0))
            if op_type == OperandType.TRAILING_PEAK_OFFSET:
                current_price = self._state_current_price(state)
                side = str(state.get("side") or "BUY").upper()
                peak_price = float(state.get("peak_price", current_price) or current_price)
                return (current_price - peak_price) if side == "SELL" else (peak_price - current_price)
            if op_type == OperandType.POSITION_RR_RATIO:
                sl_dist = float(state.get("sl_distance") or 0.0)
                if sl_dist > 0:
                    return self._state_pnl_points(state) / sl_dist
                return 0.0

            
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
            daily_open = target_df["open"].resample("1d").first().dropna()
            aligned = fast_ffill_align_float(daily_open.index.values.astype(np.int64), daily_open.values, target_df.index.values.astype(np.int64))
            price_series = pd.Series(aligned, index=target_df.index)
        elif op_type == OperandType.PREV_WEEK_HIGH:
            weekly_high = target_df["high"].resample("W").max().shift(1).dropna()
            aligned = fast_ffill_align_float(weekly_high.index.values.astype(np.int64), weekly_high.values, target_df.index.values.astype(np.int64))
            price_series = pd.Series(aligned, index=target_df.index)
        elif op_type == OperandType.PREV_WEEK_LOW:
            weekly_low = target_df["low"].resample("W").min().shift(1).dropna()
            aligned = fast_ffill_align_float(weekly_low.index.values.astype(np.int64), weekly_low.values, target_df.index.values.astype(np.int64))
            price_series = pd.Series(aligned, index=target_df.index)
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
        if op_type in INDICATOR_OPERANDS:
            series = target_engine.get_series(op_type, params)
            if series is not None and shift_val > 0:
                series = series.shift(shift_val)
            return series

        logger.warning("Unsupported op_type: %s", op_type)
        return self._nan_series()


    def _compare(self, value_1, operator, value_2):
        """
        Perform comparison between two series or a series and a scalar.
        """
        # Align indices if both are Series with different indices
        if isinstance(value_1, pd.Series) and isinstance(value_2, pd.Series):
            if not value_1.index.equals(value_2.index):
                # Align value_2 to value_1's index using forward-fill
                if value_2.dtype == bool:
                    aligned_vals = fast_ffill_align_bool(
                        value_2.index.values.astype(np.int64), 
                        value_2.values, 
                        value_1.index.values.astype(np.int64)
                    )
                    value_2 = pd.Series(aligned_vals, index=value_1.index)
                else:
                    aligned_vals = fast_ffill_align_float(
                        value_2.index.values.astype(np.int64), 
                        value_2.values, 
                        value_1.index.values.astype(np.int64)
                    )
                    value_2 = pd.Series(aligned_vals, index=value_1.index)
        
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
        elif operator == ComparisonOperator.NOT_EQUAL:
            result = value_1 != value_2
        elif operator == ComparisonOperator.CROSSES_ABOVE:
            if not isinstance(value_1, pd.Series):
                return self._false_series()
            val2_arr = value_2.values if isinstance(value_2, pd.Series) else np.full(len(value_1), float(value_2))
            res_arr = _fast_crosses_above(value_1.values.astype(np.float64), val2_arr.astype(np.float64))
            result = pd.Series(res_arr, index=value_1.index)
        elif operator == ComparisonOperator.CROSSES_BELOW:
            if not isinstance(value_1, pd.Series):
                return self._false_series()
            val2_arr = value_2.values if isinstance(value_2, pd.Series) else np.full(len(value_1), float(value_2))
            res_arr = _fast_crosses_below(value_1.values.astype(np.float64), val2_arr.astype(np.float64))
            result = pd.Series(res_arr, index=value_1.index)
        else:
            logger.warning("Unsupported comparison operator: %s", operator)
            result = self._false_series()

        return self._normalize_boolean_series(result)


    def _evaluate_custom_expression(self, params, state=None, target_df=None):
        expression_config = params.get("expression") if isinstance(params, dict) else None
        if isinstance(expression_config, dict):
            expression = str(expression_config.get("expression") or "").strip()
            variables = expression_config.get("variables") or {}
        else:
            expression = str(expression_config or "").strip()
            variables = params.get("variables") or {}

        if not expression:
            logger.warning("Custom rule missing expression")
            return self._false_series()

        if not self._is_safe_custom_expression(expression, variables=variables):
            logger.warning("Rejected unsafe custom rule expression: %s", expression)
            return self._false_series()

        eval_df = (target_df if target_df is not None else self.df).copy()
        
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
                    if series.dtype == bool:
                        aligned = fast_ffill_align_bool(series.index.values.astype(np.int64), series.values, eval_df.index.values.astype(np.int64))
                    else:
                        aligned = fast_ffill_align_float(series.index.values.astype(np.int64), series.values, eval_df.index.values.astype(np.int64))
                    series = pd.Series(aligned, index=eval_df.index)
                    
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

        if isinstance(result, pd.Series):
            return result.reindex(eval_df.index)
        return pd.Series(result, index=eval_df.index)


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
        if isinstance(series, pd.Series):
            return series.fillna(False).astype(bool)
        return pd.Series(series, index=self.df.index).fillna(False).astype(bool)

    def _state_current_price(self, state):
        value = state.get("current_price")
        if value is None and not self.df.empty:
            value = self.df["close"].iloc[-1]
        if value is None:
            value = state.get("avg_price", 0.0)
        return float(value or 0.0)

    def _state_pnl_points(self, state):
        if state.get("pnl_points") is not None:
            return float(state.get("pnl_points") or 0.0)
        avg_price = float(state.get("avg_price", 0.0) or 0.0)
        current_price = self._state_current_price(state)
        side = str(state.get("side") or "BUY").upper()
        return (avg_price - current_price) if side == "SELL" else (current_price - avg_price)

    def _state_pnl_percentage(self, state):
        if state.get("pnl_percentage") is not None:
            return float(state.get("pnl_percentage") or 0.0)
        avg_price = float(state.get("avg_price", 0.0) or 0.0)
        return (self._state_pnl_points(state) / avg_price) * 100 if avg_price else 0.0

    def _nan_series(self):
        return pd.Series(float("nan"), index=self.df.index, dtype="float64")


    def _true_series(self):
        return pd.Series(True, index=self.df.index, dtype=bool)


    def _false_series(self):
        return pd.Series(False, index=self.df.index, dtype=bool)
