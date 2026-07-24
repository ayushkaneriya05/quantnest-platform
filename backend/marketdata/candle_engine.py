import json
import logging
import pandas as pd
import redis
from django.conf import settings
from django.core.cache import cache

from marketdata.services import MarketDataService, HistoricalCandleService

logger = logging.getLogger(__name__)

try:
    redis_url = settings.CACHES["default"]["LOCATION"]
except (KeyError, AttributeError):
    redis_url = "redis://127.0.0.1:6379/1"
    
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

WORKER_LOCAL_DATAFRAMES = {}

class LiveCandleStore:
    """
    Maintains a bounded rolling buffer of candles in Redis to ensure sub-millisecond 
    access during live tick processing across multiple distributed celery workers.
    """
    MAX_BASE_WARMUP_CANDLES = 50_000
    SAFETY_BARS = 5
    
    @classmethod
    def _cache_key(cls, symbol, timeframe):
        return f"live_candle_store:{MarketDataService.normalize_symbol(symbol)}:{timeframe}"
        
    @classmethod
    def initialize(cls, symbol, timeframe, max_lookback=200):
        """
        Fetches historical data to warm up the buffer and saves to Redis.
        """
        symbol = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(timeframe)
        
        fetch_limit = min(
            int(max_lookback) + cls.SAFETY_BARS,
            cls.MAX_BASE_WARMUP_CANDLES,
        )
        
        candles = MarketDataService.list_candles(
            symbol=symbol, 
            timeframe=timeframe, 
            limit=fetch_limit
        )
        
        if not candles:
            return False
            
        key = cls._cache_key(symbol, timeframe)
        # Store as JSON strings in a Redis List
        redis_client.delete(key)
        
        if candles:
            candle_strs = [json.dumps(c) for c in candles]
            redis_client.rpush(key, *candle_strs)
            redis_client.expire(key, 60 * 60 * 24)
            
        return True

    @classmethod
    def get_candle_df(cls, symbol, timeframe, max_lookback=200, candle_state=None):
        """
        Returns a pandas DataFrame of the bounded candle buffer.
        """
        config_tf = MarketDataService.normalize_timeframe(timeframe)
        db_timeframe = "1D" if config_tf in ("1D", "1W") else "1m"
        base_key = cls._cache_key(symbol, db_timeframe)
        
        # 1. Check L1 In-Memory Cache
        local_cache = WORKER_LOCAL_DATAFRAMES.get(base_key)
        
        if local_cache is not None and candle_state and db_timeframe == "1m":
            df = local_cache["df"]
            candle_time = pd.to_datetime(candle_state["time"], unit="s", utc=True)
            
            if not df.empty and candle_time >= df.index[-1]:
                if candle_time in df.index:
                    # Update forming candle dynamically from incoming ticks
                    df.loc[candle_time, "high"] = max(df.loc[candle_time, "high"], float(candle_state["high"]))
                    df.loc[candle_time, "low"] = min(df.loc[candle_time, "low"], float(candle_state["low"]))
                    df.loc[candle_time, "close"] = float(candle_state["close"])
                else:
                    # Initialize new forming candle
                    df.loc[candle_time] = [
                        float(candle_state["open"]),
                        float(candle_state["high"]),
                        float(candle_state["low"]),
                        float(candle_state["close"]),
                        int(candle_state.get("volume", 0)),
                    ]
                
                # Calculate required base lookback to support higher timeframes safely
                base_multiplier = HistoricalCandleService.TIMEFRAME_MINUTES.get(config_tf, 1)
                base_lookback = int(max_lookback) * int(base_multiplier)
                
                # Truncate if it grows too large
                if len(df) > base_lookback + 50:
                    df = df.iloc[-int(base_lookback + 5):]
                    local_cache["df"] = df
                    
                # Update resampled L1 caches dynamically
                if "resampled" in local_cache:
                    for tf, resampled_df in local_cache["resampled"].items():
                        pd_rule = local_cache.get("pd_rules", {}).get(tf)
                        if pd_rule and not resampled_df.empty:
                            tf_boundary = candle_time.floor(pd_rule)
                            if tf_boundary in resampled_df.index:
                                resampled_df.loc[tf_boundary, "high"] = max(resampled_df.loc[tf_boundary, "high"], float(candle_state["high"]))
                                resampled_df.loc[tf_boundary, "low"] = min(resampled_df.loc[tf_boundary, "low"], float(candle_state["low"]))
                                resampled_df.loc[tf_boundary, "close"] = float(candle_state["close"])
                                resampled_df.loc[tf_boundary, "volume"] += int(candle_state.get("volume", 0))
                            else:
                                resampled_df.loc[tf_boundary] = [
                                    float(candle_state["open"]),
                                    float(candle_state["high"]),
                                    float(candle_state["low"]),
                                    float(candle_state["close"]),
                                    int(candle_state.get("volume", 0)),
                                ]
                                if len(resampled_df) > max_lookback:
                                    local_cache["resampled"][tf] = resampled_df.iloc[-int(max_lookback):]
            else:
                # Out of order tick or empty cache, force rebuild
                local_cache = None
                
        # 2. Rebuild from Redis (L2 Cache) if necessary
        if local_cache is None:
            list_len = redis_client.llen(base_key)
            
            if list_len == 0:
                # Auto-initialize base timeframe if missing
                if db_timeframe == "1D":
                    cls.initialize(symbol, "1D", int(max_lookback) * (5 if config_tf == "1W" else 1))
                else:
                    base_multiplier = HistoricalCandleService.TIMEFRAME_MINUTES.get(config_tf, 1)
                    base_lookback = int(max_lookback) * int(base_multiplier)
                    cls.initialize(symbol, "1m", base_lookback)
                    
                list_len = redis_client.llen(base_key)
                if list_len == 0:
                    return pd.DataFrame()
                    
            try:
                cached_data = redis_client.lrange(base_key, 0, -1)
                candles = [json.loads(c) for c in cached_data]
                df = pd.DataFrame(candles)
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
                    df = df.set_index("timestamp")
                    df = df[["open", "high", "low", "close", "volume"]]
                    
                    # Update Worker L1 Cache
                    local_cache = {"df": df, "resampled": {}, "pd_rules": {}}
                    WORKER_LOCAL_DATAFRAMES[base_key] = local_cache
            except Exception as exc:
                logger.exception("Failed to parse LiveCandleStore for %s %s: %s", symbol, timeframe, exc)
                return pd.DataFrame()

        if local_cache and not local_cache["df"].empty:
            df = local_cache["df"]
            
            # Use Resampled Cache if higher timeframe is requested
            if timeframe not in ("1m", "1D"):
                if timeframe in local_cache["resampled"]:
                    df = local_cache["resampled"][timeframe]
                else:
                    config_tf = MarketDataService.normalize_timeframe(timeframe)
                    # Convert QuantNest timeframe to pandas rule
                    rule_map = {
                        "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
                        "1H": "1h", "4H": "4h", "1D": "d", "1W": "W-MON"
                    }
                    pd_rule = rule_map.get(config_tf)
                    if pd_rule:
                        df = df.resample(pd_rule).agg({
                            "open": "first",
                            "high": "max",
                            "low": "min",
                            "close": "last",
                            "volume": "sum"
                        }).dropna()
                        local_cache["resampled"][timeframe] = df
                        local_cache["pd_rules"][timeframe] = pd_rule
            
            # Ensure we strictly bound the buffer to requested lookback
            if len(df) > max_lookback:
                df = df.iloc[-int(max_lookback):]
            return df.copy()  # Return copy to prevent strategies from mutating the cache
            
        return pd.DataFrame()

    @classmethod
    def update_buffer(cls, symbol, timeframe, latest_candle_state, max_lookback=200):
        """
        Updates the end of the rolling buffer with a live forming candle or newly closed candle.
        latest_candle_state should be a dict matching the serialized candle format.
        """
        key = cls._cache_key(symbol, timeframe)
        
        last_str = redis_client.lindex(key, -1)
        if not last_str:
            # Need historical data first
            cls.initialize(symbol, timeframe, max_lookback)
            last_str = redis_client.lindex(key, -1)
            if not last_str:
                return False
                
        try:
            last_candle = json.loads(last_str)
            candle_time = int(latest_candle_state["time"])
            
            # Check if this updates the current forming candle or starts a new one
            if last_candle["time"] == candle_time:
                # Update forming candle
                last_candle["high"] = max(last_candle["high"], float(latest_candle_state["high"]))
                last_candle["low"] = min(last_candle["low"], float(latest_candle_state["low"]))
                last_candle["close"] = float(latest_candle_state["close"])
                # For 1D the volume from broker is already total daily volume. For 1m it is total 1m volume.
                last_candle["volume"] = int(latest_candle_state.get("volume", last_candle.get("volume", 0)))
                
                redis_client.lset(key, -1, json.dumps(last_candle))
            else:
                # Append new candle
                new_candle = {
                    "time": candle_time,
                    "open": float(latest_candle_state["open"]),
                    "high": float(latest_candle_state["high"]),
                    "low": float(latest_candle_state["low"]),
                    "close": float(latest_candle_state["close"]),
                    "volume": int(latest_candle_state.get("volume", 0)),
                }
                
                redis_client.rpush(key, json.dumps(new_candle))
                
                # Bound the array to prevent unbounded growth in Redis
                list_len = redis_client.llen(key)
                if list_len > max_lookback + 5:
                    redis_client.ltrim(key, -(max_lookback + 5), -1)
                    
            redis_client.expire(key, 60 * 60 * 24)
            return True
            
        except Exception as exc:
            logger.exception("Failed to update LiveCandleStore buffer for %s %s: %s", symbol, timeframe, exc)
            return False
