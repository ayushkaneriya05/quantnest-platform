import pandas as pd
from datetime import datetime, timezone

class DataPreprocessor:
    """
    Handles fetching shared memory ticks and resampling them into 
    Pandas DataFrames for the Strategy Executor.
    """
    @staticmethod
    def build_mtf_data(shm, executor):
        """
        Fetches the latest data from shared memory, constructs the 1m DataFrame,
        performs any necessary multi-timeframe resampling requested by the strategy,
        and injects it into the executor.
        
        Returns:
            Tuple[pd.DataFrame, datetime]: The base dataframe for the primary timeframe, 
                                           and the exact evaluation timestamp.
        """
        latest_data = shm.get_latest_data()
        
        # We need a Pandas DataFrame for the legacy executor for now.
        df = pd.DataFrame(latest_data, columns=["open", "high", "low", "close", "volume", "epoch"])
        df = df[df["open"] > 0] # Filter out empty pre-allocated rows
        
        if len(df) == 0:
            return None, None
            
        timestamp = datetime.now(timezone.utc)
        known_epochs = df["epoch"].where(df["epoch"] > 0)
        fallback_end = timestamp.replace(second=0, microsecond=0)
        reconstructed = pd.to_datetime(known_epochs, unit="s", utc=True, errors="coerce")
        if reconstructed.notna().all():
            df.index = reconstructed
        else:
            df.index = pd.date_range(end=fallback_end, periods=len(df), freq="1min")
        df = df.drop(columns=["epoch"])
        
        # --- DYNAMIC MTF RESAMPLING ---
        from marketdata.access import StrategyMarketDataService
        base_tf, req_tfs = StrategyMarketDataService.required_timeframes(executor.config)
        
        mtf_data = {"1m": df}
        
        if base_tf != "1m":
            req_tfs.add(base_tf)
            
        for tf in req_tfs:
            if tf != "1m":
                # Convert tf string ("5m", "15m", "1D", "1W") to Pandas freq ("5min", "15min", "D", "W")
                pandas_freq = tf.replace("m", "min").replace("1D", "D").replace("1W", "W")
                resampled = df.resample(pandas_freq).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                mtf_data[tf] = resampled
                
        # Inject the parsed MTF data into the executor cache
        executor.mtf_data = mtf_data
        
        base_df = mtf_data.get(base_tf, df)
        return base_df, timestamp
