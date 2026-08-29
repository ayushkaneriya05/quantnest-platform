import pandas as pd
from datetime import timedelta, datetime, date, time
from django.utils import timezone
from datetime import timezone as py_timezone
from .services import MarketDataService


class StrategyMarketDataService:
    """
    Shared access layer for strategy consumers.

    This keeps paper/live/backtest execution code away from the lower-level
    marketdata cache and storage details.
    """

    @classmethod
    def get_backtest_multi_timeframe_data(cls, config, instrument, *, start_dt, end_dt, fetch_missing=True):
        if instrument is None:
            return None, {}

        base_timeframe, required_timeframes = cls.required_timeframes(config)
        mtf_data = {}
        for timeframe in required_timeframes:
            df = cls.get_backtest_candles(
                symbol=instrument.sym_ticker,
                resolution=timeframe,
                start_dt=start_dt,
                end_dt=end_dt,
                fetch_missing=fetch_missing,
                clean=True,
            )
            if df is not None and not df.empty:
                mtf_data[timeframe] = df

        return base_timeframe, mtf_data

    @staticmethod
    def required_timeframes(config):
        time_rule = (config or {}).get("time_rule") or {}
        base_timeframe = MarketDataService.normalize_timeframe(time_rule.get("candle_timeframe", "1m"))
        required_timeframes = {base_timeframe}
        for group in (config or {}).get("rule_groups", []) or []:
            for rule in group.get("rules", []) or []:
                    tf_a = rule.get("operand_a_timeframe")
                    if tf_a:
                        required_timeframes.add(MarketDataService.normalize_timeframe(tf_a))
                        
                    tf_b = rule.get("operand_b_timeframe")
                    if tf_b:
                        required_timeframes.add(MarketDataService.normalize_timeframe(tf_b))
        return base_timeframe, required_timeframes

    @classmethod
    def get_backtest_candles(
        cls,
        symbol,
        resolution,
        start_dt,
        end_dt,
        fetch_missing=True,
        clean=True,
    ):

        timeframe = MarketDataService.normalize_timeframe(resolution)
        
        def _coerce_datetime(value, start_of_day):
            if isinstance(value, datetime):
                if timezone.is_naive(value):
                    return timezone.make_aware(value, py_timezone.utc)
                return value
            if isinstance(value, date):
                base = datetime.combine(value, time.min if start_of_day else time.max)
                return timezone.make_aware(base, py_timezone.utc)
            raise TypeError(f"Unsupported date value: {value!r}")

        start_dt = _coerce_datetime(start_dt, start_of_day=True)
        end_dt = _coerce_datetime(end_dt, start_of_day=False)
        db_timeframe = "1D" if timeframe in {"1D", "1W"} else "1m"

        candles = MarketDataService.list_candles(
            symbol=symbol,
            timeframe=db_timeframe,
            limit=None,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        needs_fetch = False
        if fetch_missing:
            if not candles:
                needs_fetch = True
            else:
                first_candle_dt = datetime.fromtimestamp(candles[0]["time"], tz=py_timezone.utc).date()
                last_candle_dt = datetime.fromtimestamp(candles[-1]["time"], tz=py_timezone.utc).date()
                if (first_candle_dt - start_dt.date()).days > 4 or (end_dt.date() - last_candle_dt).days > 4:
                    needs_fetch = True

        if needs_fetch:
            chunk_start = start_dt.date()
            end_date_limit = end_dt.date()
            
            while chunk_start <= end_date_limit:
                chunk_end = min(chunk_start + timedelta(days=90), end_date_limit)
                MarketDataService.backfill_candles_from_broker(
                    symbol=symbol,
                    date_from=chunk_start.isoformat(),
                    date_to=chunk_end.isoformat(),
                    timeframe=db_timeframe,
                )
                chunk_start = chunk_end + timedelta(days=1)

        dict_candles = MarketDataService.list_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=None,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        df = pd.DataFrame(dict_candles)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.drop(columns=["time"])
        if clean:
            return cls.normalize_candles_df(df)
        return df

    @classmethod
    def normalize_candles_df(cls, df):
        import pandas as pd
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        normalized = df.copy()
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"])
        normalized = normalized.sort_values("timestamp")
        normalized = normalized.drop_duplicates(subset=["timestamp"], keep="last")
        normalized = normalized.set_index("timestamp")
        normalized.index.name = "timestamp"
        return normalized[["open", "high", "low", "close", "volume"]]
