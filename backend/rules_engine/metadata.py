from common.enums import IndicatorType, PriceActionType, VolumeConditionType
from common.trading_utils import get_any_field

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
            for collection_name in ("rules", "stop_loss_rules", "target_rules"):
                for rule in group.get(collection_name, []) or []:
                    if not get_any_field(rule, "is_active", True):
                        continue
                        
                    tf_override = get_any_field(rule, "timeframe_override")
                    timeframe = tf_override if tf_override else base_timeframe
                    
                    lookback = cls._calculate_rule_lookback(rule)
                    if timeframe not in requirements or lookback > requirements[timeframe]:
                        requirements[timeframe] = lookback
                        
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
    def _calculate_rule_lookback(cls, rule):
        indicator_type = get_any_field(rule, "indicator_type")
        price_action_type = get_any_field(rule, "price_action_type")
        volume_condition_type = get_any_field(rule, "volume_condition_type")
        params = get_any_field(rule, "params", {}) or {}
        
        lookback = cls.MIN_LOOKBACK
        
        if indicator_type:
            lookback = cls._get_indicator_lookback(indicator_type, params)
        elif price_action_type:
            lookback = max(int(params.get("lookback", params.get("period", 20))), 5)
        elif volume_condition_type:
            lookback = max(int(params.get("period", 20)), 10)
            
        return lookback
        
    @classmethod
    def _get_indicator_lookback(cls, indicator_type, params):
        # Using same defaults as IndicatorEngine
        period = int(params.get("period", params.get("length", 14)))
        
        # EMAs and derivatives need a longer "unstable period" to settle
        # Usually 3x to 5x the period is standard practice
        if indicator_type in {IndicatorType.EMA, IndicatorType.WMA}:
            return period * 5
            
        elif indicator_type in {IndicatorType.MACD, IndicatorType.MACD_SIGNAL, IndicatorType.MACD_HISTOGRAM}:
            slow = int(params.get("slow_period", params.get("slow", 26)))
            signal = int(params.get("signal_period", params.get("signal", 9)))
            return (slow + signal) * 5
            
        elif indicator_type == IndicatorType.RSI:
            return period * 5  # Wilder's Smoothing needs significant warmup
            
        elif indicator_type == IndicatorType.VWAP:
            return 400  # VWAP usually resets daily, 400 mins is ~1 trading day
            
        elif indicator_type == IndicatorType.SUPERTREND:
            return period * 5  # Uses ATR which uses EMA/RMA internally
            
        elif indicator_type in {IndicatorType.ADX, IndicatorType.PLUS_DI, IndicatorType.MINUS_DI}:
            return period * 5
            
        elif indicator_type in {IndicatorType.STOCHASTIC_K, IndicatorType.STOCHASTIC_D}:
            k = int(params.get("k_period", params.get("k", 14)))
            d = int(params.get("d_period", params.get("d", 3)))
            smooth = int(params.get("smooth", params.get("smooth_k", 3)))
            return k + d + smooth
            
        elif indicator_type == IndicatorType.ATR:
            return period * 5
            
        elif indicator_type in {IndicatorType.SMA, IndicatorType.BOLLINGER_UPPER, IndicatorType.BOLLINGER_MID, IndicatorType.BOLLINGER_LOWER}:
            # Simple averages don't have unstable periods, they just need N candles
            return period
            
        return max(period, cls.MIN_LOOKBACK)
