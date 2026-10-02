import logging

import pandas as pd
from datetime import timedelta, datetime, date, time
from django.utils import timezone
from datetime import timezone as py_timezone
from .calendar import MarketSessionCalendar
from .services import MarketDataService

logger = logging.getLogger(__name__)


class StrategyMarketDataService:
    """
    Shared access layer for strategy consumers.

    This keeps paper/live/backtest execution code away from the lower-level
    marketdata cache and storage details.
    """

    @classmethod
    def get_backtest_multi_timeframe_data(cls, config, instrument, *, start_dt, end_dt, fetch_missing=True, calendar=None):
        if instrument is None:
            return None, {}, {"complete": False, "missing": []}

        base_timeframe, required_timeframes = cls.required_timeframes(config)
        calendar = calendar or MarketSessionCalendar.for_instrument(instrument)
        mtf_data = {}
        quality = {"instrument": instrument.sym_ticker, "complete": True, "timeframes": {}}
        ordered_timeframes = [base_timeframe] + sorted(required_timeframes - {base_timeframe})
        backfilled_families = set()
        for timeframe in ordered_timeframes:
            family = "daily" if timeframe in {"1D", "1W"} else "intraday"
            should_fetch_missing = fetch_missing and family not in backfilled_families
            df, coverage = cls.get_backtest_candles(
                symbol=instrument.sym_ticker,
                resolution=timeframe,
                start_dt=start_dt,
                end_dt=end_dt,
                fetch_missing=should_fetch_missing,
                clean=True,
                calendar=calendar,
            )
            backfilled_families.add(family)
            quality["timeframes"][timeframe] = coverage
            quality["complete"] = quality["complete"] and coverage["complete"]
            if df is not None and not df.empty:
                mtf_data[timeframe] = df

        return base_timeframe, mtf_data, quality

    @staticmethod
    def required_timeframes(config):
        time_rule = (config or {}).get("time_rule") or {}
        base_timeframe = MarketDataService.normalize_timeframe(time_rule.get("candle_timeframe", "1m"))
        from rules_engine.metadata import IndicatorRequirementAnalyzer

        requirements = IndicatorRequirementAnalyzer.get_warmup_requirements(config or {})
        required_timeframes = {
            MarketDataService.normalize_timeframe(timeframe) for timeframe in requirements
        }
        required_timeframes.add(base_timeframe)
        return base_timeframe, required_timeframes

    @classmethod
    def get_backtest_candles(cls, symbol, resolution, start_dt, end_dt, fetch_missing=True, clean=True, calendar=None):
        timeframe = MarketDataService.normalize_timeframe(resolution)
        calendar = calendar or MarketSessionCalendar.for_symbol(symbol)
        start_dt = cls._coerce_datetime(start_dt, start_of_day=True, calendar=calendar)
        end_dt = cls._coerce_datetime(end_dt, start_of_day=False, calendar=calendar)
        source_timeframe = "1D" if timeframe in {"1D", "1W"} else "1m"

        source_candles = MarketDataService.list_candles(
            symbol=symbol,
            timeframe=source_timeframe,
            limit=None,
            start_dt=start_dt,
            end_dt=end_dt,
            calendar=calendar,
        )

        source_coverage = calendar.coverage(source_candles, source_timeframe, start_dt, end_dt)
        if fetch_missing and source_coverage["missing_dates"]:
            for date_from, date_to in cls._date_ranges(source_coverage["missing_dates"]):
                fetched = MarketDataService.backfill_candles_from_broker(
                    symbol=symbol,
                    date_from=date_from.isoformat(),
                    date_to=date_to.isoformat(),
                    timeframe=source_timeframe,
                )
                if fetched is None:
                    logger.warning("Broker backfill failed for %s %s from %s through %s", symbol, source_timeframe, date_from, date_to)

            source_candles = MarketDataService.list_candles(
                symbol=symbol,
                timeframe=source_timeframe,
                limit=None,
                start_dt=start_dt,
                end_dt=end_dt,
                calendar=calendar,
            )
            source_coverage = calendar.coverage(source_candles, source_timeframe, start_dt, end_dt)
        source_coverage["source_timeframe"] = source_timeframe
        if not source_coverage["complete"]:
            logger.error(
                "Backtest data remains incomplete for %s %s after broker backfill: %d missing candle(s)",
                symbol,
                source_timeframe,
                source_coverage["missing_count"],
            )

        candles = source_candles if timeframe == source_timeframe else MarketDataService.list_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=None,
            start_dt=start_dt,
            end_dt=end_dt,
            calendar=calendar,
        )
        df = pd.DataFrame(candles)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]), {
                **source_coverage,
                "complete": False,
                "missing_dates": [value.isoformat() for value in source_coverage["missing_dates"]],
                "available_count": 0,
            }
            
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.drop(columns=["time"])
        if clean:
            df = cls.normalize_candles_df(df)
        return df, {
            **source_coverage,
            "missing_dates": [value.isoformat() for value in source_coverage["missing_dates"]],
        }

    @staticmethod
    def _coerce_datetime(value, *, start_of_day, calendar):
        if isinstance(value, datetime):
            return timezone.make_aware(value, py_timezone.utc) if timezone.is_naive(value) else value
        if isinstance(value, date):
            clock = time.min if start_of_day else time.max
            return datetime.combine(value, clock, tzinfo=calendar.zone)
        raise TypeError(f"Unsupported date value: {value!r}")

    @staticmethod
    def _date_ranges(days):
        if not days:
            return []
        days = sorted(set(days))
        ranges = []
        start = previous = days[0]
        def append_chunks(first, last):
            while first <= last:
                chunk_end = min(first + timedelta(days=89), last)
                ranges.append((first, chunk_end))
                first = chunk_end + timedelta(days=1)
        for current in days[1:]:
            if current != previous + timedelta(days=1):
                append_chunks(start, previous)
                start = current
            previous = current
        append_chunks(start, previous)
        return ranges

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
