import json
import logging
import pandas as pd
from django.core.cache import cache

from marketdata.services import MarketDataService, HistoricalCandleService

logger = logging.getLogger(__name__)

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
        # Store as JSON for cross-worker safety
        cache.set(key, json.dumps(candles), timeout=60 * 60 * 24)
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
                    WORKER_LOCAL_DATAFRAMES[base_key] = {"df": df}
            else:
                # Out of order tick or empty cache, force rebuild
                local_cache = None
                
        # 2. Rebuild from Redis (L2 Cache) if necessary
        if local_cache is None:
            cached_data = cache.get(base_key)
            
            if not cached_data:
                # Auto-initialize base timeframe if missing
                if db_timeframe == "1D":
                    cls.initialize(symbol, "1D", int(max_lookback) * (5 if config_tf == "1W" else 1))
                else:
                    base_multiplier = HistoricalCandleService.TIMEFRAME_MINUTES.get(config_tf, 1)
                    base_lookback = int(max_lookback) * int(base_multiplier)
                    cls.initialize(symbol, "1m", base_lookback)
                    
                cached_data = cache.get(base_key)
                if not cached_data:
                    return pd.DataFrame()
                    
            try:
                candles = json.loads(cached_data)
                df = pd.DataFrame(candles)
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
                    df = df.set_index("timestamp")
                    df = df[["open", "high", "low", "close", "volume"]]
                    
                    # Update Worker L1 Cache
                    WORKER_LOCAL_DATAFRAMES[base_key] = {"df": df}
            except Exception as exc:
                logger.exception("Failed to parse LiveCandleStore for %s %s: %s", symbol, timeframe, exc)
                return pd.DataFrame()
        else:
            df = local_cache["df"].copy() if local_cache else pd.DataFrame()

        if not df.empty:
            # Resample if higher timeframe is requested
            if timeframe not in ("1m", "1D"):
                config_tf = MarketDataService.normalize_timeframe(timeframe)
                # Convert QuantNest timeframe to pandas rule
                rule_map = {
                    "3m": "3T", "5m": "5T", "15m": "15T", "30m": "30T",
                    "1H": "1H", "4H": "4H", "1D": "D", "1W": "W-MON"
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
        cached_data = cache.get(key)
        
        if not cached_data:
            # Need historical data first
            cls.initialize(symbol, timeframe, max_lookback)
            cached_data = cache.get(key)
            if not cached_data:
                return False
                
        try:
            candles = json.loads(cached_data)
            candle_time = int(latest_candle_state["time"])
            
            # Check if this updates the current forming candle or starts a new one
            if candles and candles[-1]["time"] == candle_time:
                # Update forming candle
                current = candles[-1]
                current["high"] = max(current["high"], float(latest_candle_state["high"]))
                current["low"] = min(current["low"], float(latest_candle_state["low"]))
                current["close"] = float(latest_candle_state["close"])
                # For 1D the volume from broker is already total daily volume. For 1m it is total 1m volume.
                current["volume"] = int(latest_candle_state.get("volume", current["volume"]))
            else:
                # Append new candle
                candles.append({
                    "time": candle_time,
                    "open": float(latest_candle_state["open"]),
                    "high": float(latest_candle_state["high"]),
                    "low": float(latest_candle_state["low"]),
                    "close": float(latest_candle_state["close"]),
                    "volume": int(latest_candle_state.get("volume", 0)),
                })
                
            # Bound the array to prevent unbounded growth
            if len(candles) > max_lookback + 5:
                candles = candles[-(max_lookback + 5):]
                
            cache.set(key, json.dumps(candles), timeout=60 * 60 * 24)
            return True
            
        except Exception as exc:
            logger.exception("Failed to update LiveCandleStore buffer for %s %s: %s", symbol, timeframe, exc)
            return False
