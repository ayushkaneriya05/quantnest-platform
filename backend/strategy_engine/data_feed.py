
"""Calendar-aligned completed frames, reused across strategies and calculation turns."""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

FRAME_CACHE = OrderedDict()
MAX_CACHED_FRAMES = 64


def completed_horizon(calendar, timeframe, as_of):
    from marketdata.calendar import INTRADAY_MINUTES
    local = as_of.astimezone(calendar.zone)
    day = local.date()
    if timeframe == "1W":
        monday = day - timedelta(days=day.weekday())
        for shift in range(0, 371, 7):
            start = monday - timedelta(days=shift)
            sessions = [start + timedelta(days=offset) for offset in range(7)
                        if calendar.is_trading_day(start + timedelta(days=offset))]
            if sessions:
                closing = calendar.session_close(sessions[-1])
                if closing <= local:
                    return closing.timestamp()
        raise ValueError("No completed trading week exists in the loaded calendar")
    while not calendar.is_trading_day(day) or calendar.session_open(day) >= local:
        day -= timedelta(days=1)
    opening, closing = calendar.session_open(day), calendar.session_close(day)
    if timeframe == "1D":
        if local < closing:
            day -= timedelta(days=1)
            while not calendar.is_trading_day(day):
                day -= timedelta(days=1)
        return calendar.session_close(day).timestamp()
    step = INTRADAY_MINUTES[timeframe] * 60
    if local >= closing:
        return closing.timestamp()
    return (opening + timedelta(seconds=int((local - opening).total_seconds() // step) * step)).timestamp()


class DataPreprocessor:
    @staticmethod
    def build_mtf_data(shm, executor, calendar=None, as_of=None):
        if calendar is None:
            raise ValueError("Preload an exchange calendar before evaluation")
        as_of = as_of or datetime.now(timezone.utc)
        horizons = tuple((tf, completed_horizon(calendar, tf, as_of)) for tf in sorted(executor.required_timeframes))
        key = (shm.symbol, shm.history_revision, horizons, executor.evaluation_lookback_1m,
               calendar.timezone_name, calendar.market_open, calendar.market_close)
        frames = FRAME_CACHE.get(key)
        if frames is None:
            rows = shm.get_latest_data(executor.evaluation_lookback_1m)
            df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume", "epoch"])
            df = df[(df["open"] > 0) & (df["epoch"] > 0)]
            if df.empty:
                return None, None
            df.index = pd.to_datetime(df.pop("epoch"), unit="s", utc=True)
            df = df[~df.index.duplicated(keep="last")].sort_index()
            local = df.index.tz_convert(calendar.zone)
            naive = local.tz_localize(None)
            dates = local.date
            unique_dates = set(dates)
            closes = {day: calendar.session_close(day).time() for day in unique_dates}
            valid = np.array([calendar.is_trading_day(day) and calendar.market_open <= stamp.time() < closes[day]
                              for day, stamp in zip(dates, local)])
            opening_delta = pd.Timedelta(hours=calendar.market_open.hour, minutes=calendar.market_open.minute)
            daily_open = naive.normalize() + opening_delta
            frames = {}
            from marketdata.calendar import INTRADAY_MINUTES
            aggregation = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
            for timeframe in executor.required_timeframes:
                if timeframe in INTRADAY_MINUTES:
                    step = INTRADAY_MINUTES[timeframe]
                    minutes = (naive - daily_open).total_seconds() // 60
                    buckets = daily_open + pd.to_timedelta((minutes // step) * step, unit="min")
                elif timeframe == "1D":
                    buckets = daily_open
                else:
                    buckets = naive.normalize() - pd.to_timedelta(naive.dayofweek, unit="D")
                buckets = buckets.tz_localize(calendar.zone).tz_convert(timezone.utc)
                selected = df.loc[valid].copy()
                selected["bucket"] = buckets[valid]
                grouped = selected.groupby("bucket").agg(aggregation)
                counts = selected.groupby("bucket").size()
                available = []
                keep = []
                for index, stamp in enumerate(grouped.index):
                    start = stamp.to_pydatetime()
                    end = calendar.candle_close(start, timeframe)
                    scheduled = end.astimezone(timezone.utc)
                    local_start = start.astimezone(calendar.zone)
                    if timeframe == "1W":
                        expected = sum(int((calendar.session_close(local_start.date() + timedelta(days=offset)) -
                                            calendar.session_open(local_start.date() + timedelta(days=offset))).total_seconds() // 60)
                                       for offset in range(7) if calendar.is_trading_day(local_start.date() + timedelta(days=offset)))
                    else:
                        expected = int((end - (calendar.session_open(local_start.date()) if timeframe == "1D" else local_start)).total_seconds() // 60)
                    complete = int(counts.iloc[index]) == expected
                    if scheduled <= as_of and not complete and index > 0:
                        raise ValueError(f"Missing source minutes in completed {timeframe} candle for {shm.symbol}")
                    available.append(scheduled)
                    keep.append(scheduled <= as_of and complete)
                grouped.index = pd.DatetimeIndex(available)
                frames[timeframe] = grouped.loc[keep]
            FRAME_CACHE[key] = frames
            FRAME_CACHE.move_to_end(key)
            from django.conf import settings
            budget = settings.CALCULATION_CACHE_MB * 1024 * 1024
            def size(value):
                return sum(int(frame.memory_usage(index=True, deep=True).sum()) for frame in value.values())
            used = sum(size(value) for value in FRAME_CACHE.values())
            while FRAME_CACHE and (len(FRAME_CACHE) > MAX_CACHED_FRAMES or used > budget):
                _, evicted = FRAME_CACHE.popitem(last=False)
                used -= size(evicted)
        executor.mtf_data = frames
        base = frames.get(executor.base_timeframe)
        return (base, base.index[-1].to_pydatetime()) if base is not None and not base.empty else (None, None)
