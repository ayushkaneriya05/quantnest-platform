from common.enums import OperandType
from common.trading_utils import get_any_field
from rules_engine.indicators import INDICATOR_OPERANDS

class IndicatorRequirementAnalyzer:
    """
    Analyzes a strategy configuration and computes the required historical 
    candle lookback (warmup period) for each required timeframe.
    """
    
    # Minimum default lookback if an indicator has no specific period
    MIN_LOOKBACK = 20
    
    @classmethod
    def get_warmup_requirements(cls, config):
        """
        Returns a dict mapping timeframe -> required number of candles.
        e.g., {"1m": 150, "15m": 50}
        """
        requirements = {}
        
        time_rule = (config or {}).get("time_rule") or {}
        base_timeframe = time_rule.get("candle_timeframe", "1m")
        
        # Initialize base timeframe
        requirements[base_timeframe] = cls.MIN_LOOKBACK
        
        groups = (config or {}).get("rule_groups", []) or []
        for group in groups:
            for rule in group.get("rules", []) or []:
                    if not get_any_field(rule, "is_active", True):
                        continue
                        
                    tf_a = get_any_field(rule, "operand_a_timeframe") or base_timeframe
                    tf_b = get_any_field(rule, "operand_b_timeframe") or base_timeframe
                    
                    lookback_a = cls._calculate_operand_lookback(
                        get_any_field(rule, "operand_a_type"),
                        get_any_field(rule, "operand_a_params", {}) or {}
                    )
                    if tf_a not in requirements or lookback_a > requirements[tf_a]:
                        requirements[tf_a] = lookback_a
                        
                    lookback_b = cls._calculate_operand_lookback(
                        get_any_field(rule, "operand_b_type"),
                        get_any_field(rule, "operand_b_params", {}) or {}
                    )
                    if tf_b not in requirements or lookback_b > requirements[tf_b]:
                        requirements[tf_b] = lookback_b
                        
        return requirements

    @classmethod
    def get_max_warmup_days(cls, config):
        """
        Converts the candle requirements into calendar days needed to fetch the data.
        Assumes ~375 minutes per trading day for intraday, 1 for daily, 7 for weekly.
        """
        requirements = cls.get_warmup_requirements(config)
        max_days = 0
        
        for timeframe, candles in requirements.items():
            if timeframe in {"1W", "W"}:
                days = candles * 7
            elif timeframe in {"1D", "D"}:
                days = candles * 2  # *2 to account for weekends/holidays
            else:
                # Intraday. 1 day = 375 mins. We add *2 for weekends
                days = max((candles * 2) // 300, 2)
            max_days = max(max_days, days)
            
        return max_days

    @classmethod
    def _calculate_operand_lookback(cls, op_type, params):
        if not op_type:
            return 0
            
        lookback = cls.MIN_LOOKBACK
        if op_type in INDICATOR_OPERANDS:
            lookback = cls._get_indicator_lookback(op_type, params)
            
        # Add recursive source check
        source = params.get("source")
        if source:
            source_params = params.get("source_params", {})
            try:
                source_op = OperandType(source)
                source_lookback = cls._calculate_operand_lookback(source_op, source_params)
                lookback = max(lookback, source_lookback)
            except ValueError:
                pass
                
        return lookback
        
    @classmethod
    def _get_indicator_lookback(cls, indicator_type, params):
        # Using same defaults as IndicatorEngine
        period = int(params.get("period", params.get("length", 14)))
        
        # EMAs and derivatives need a longer "unstable period" to settle
        # Usually 3x to 5x the period is standard practice
        if indicator_type in {OperandType.EMA, OperandType.WMA}:
            return period * 5
            
        elif indicator_type == OperandType.MACD:
            slow = int(params.get("slow_period", params.get("slow", 26)))
            signal = int(params.get("signal_period", params.get("signal", 9)))
            return (slow + signal) * 5
            
        elif indicator_type == OperandType.RSI:
            return period * 5  # Wilder's Smoothing needs significant warmup
            
        elif indicator_type == OperandType.VWAP:
            return 400  # VWAP usually resets daily, 400 mins is ~1 trading day
            
        elif indicator_type == OperandType.SUPERTREND:
            return period * 5  # Uses ATR which uses EMA/RMA internally
            
        elif indicator_type in {OperandType.ADX, OperandType.DMI}:
            return period * 5
            
        elif indicator_type == OperandType.STOCHASTIC:
            k = int(params.get("k_period", params.get("k", 14)))
            d = int(params.get("d_period", params.get("d", 3)))
            smooth = int(params.get("smooth", params.get("smooth_k", 3)))
            return k + d + smooth
            
        elif indicator_type == OperandType.ATR:
            return period * 5
            
        elif indicator_type in {OperandType.SMA, OperandType.BOLLINGER_BANDS}:
            # Simple averages don't have unstable periods, they just need N candles
            return period
            
        elif indicator_type == OperandType.CANDLE_PATTERN:
            return 5
            
        return max(period, cls.MIN_LOOKBACK)
