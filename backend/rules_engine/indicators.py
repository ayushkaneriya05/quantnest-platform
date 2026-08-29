import json
import logging
import pandas as pd
import numpy as np

if not hasattr(np, "NaN"):
    np.NaN = np.nan

import pandas_ta as ta
from datetime import datetime
from common.enums import OperandType
from common.trading_utils import to_float
from .math_utils import fast_ffill_align_float, fast_sma, fast_ema

logger = logging.getLogger(__name__)

INDICATOR_OPERANDS = {
    OperandType.SMA, OperandType.EMA, OperandType.WMA, OperandType.HMA, OperandType.ALMA, OperandType.KAMA, OperandType.DEMA, OperandType.TEMA,
    OperandType.RSI, OperandType.ROC, OperandType.MACD, OperandType.BOLLINGER_BANDS, OperandType.SUPERTREND, OperandType.ADX, OperandType.DMI, OperandType.STOCHASTIC, OperandType.ATR,
    OperandType.CCI, OperandType.WILLIAMS_R, OperandType.OBV, OperandType.MFI, OperandType.PIVOT_POINT, OperandType.KELTNER_CHANNEL, OperandType.DONCHIAN_CHANNEL, OperandType.PARABOLIC_SAR, OperandType.ICHIMOKU_CLOUD,
    OperandType.VWAP, OperandType.CANDLE_PATTERN
}

class IndicatorEngine:
    """
    Computes technical indicators using pandas_ta and caches them.
    Abstracted from RuleEvaluator to adhere to single responsibility principle.
    """
    def __init__(self, df):
        self.df = df
        self._recursion_depth = 0
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
        open_ = self.df["open"]
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
                res = fast_sma(close.values.astype(np.float64), p["period"])
                series = pd.Series(res, index=self.df.index)
            elif indicator_type == OperandType.EMA:
                res = fast_ema(close.values.astype(np.float64), p["period"])
                series = pd.Series(res, index=self.df.index)
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
                    
                pattern_df = ta.cdl_pattern(open_, high, low, close, name=pattern_name)
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
                        
                        # Keep as boolean so it triggers correctly without an explicit comparison
                        series = series.astype(bool)

        except Exception as exc:
            logger.exception("Error calculating indicator %s: %s", indicator_type, exc)
            series = None

        if series is None:
            logger.warning("Unsupported or failed indicator: %s — returning NaN series", indicator_type)
            # Return NaN so comparisons produce False rather than
            # misleading zeros (zero could be a valid price/level).
            series = pd.Series(float("nan"), index=self.df.index, dtype="float64")

        if isinstance(series, pd.Series) and series.dtype == bool:
            series = pd.Series(series, index=self.df.index, dtype="bool")
        else:
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
        if self._recursion_depth > 5:
            logger.warning("Max recursion depth exceeded in _get_price_source")
            return self.df["close"]
            
        self._recursion_depth += 1
        try:
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
                daily_open = self.df["open"].resample("1d").first().dropna()
                aligned = fast_ffill_align_float(daily_open.index.values.astype(np.int64), daily_open.values, self.df.index.values.astype(np.int64))
                price_series = pd.Series(aligned, index=self.df.index)
            elif source_str == "PREV_WEEK_HIGH":
                weekly_high = self.df["high"].resample("W").max().shift(1).dropna()
                aligned = fast_ffill_align_float(weekly_high.index.values.astype(np.int64), weekly_high.values, self.df.index.values.astype(np.int64))
                price_series = pd.Series(aligned, index=self.df.index)
            elif source_str == "PREV_WEEK_LOW":
                weekly_low = self.df["low"].resample("W").min().shift(1).dropna()
                aligned = fast_ffill_align_float(weekly_low.index.values.astype(np.int64), weekly_low.values, self.df.index.values.astype(np.int64))
                price_series = pd.Series(aligned, index=self.df.index)
    
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
        finally:
            self._recursion_depth -= 1


