"""
marketdata/access.py — Strategy market-data access layer.

All completeness-related logic is delegated to ``MarketDataRepository``.
This file is responsible for adapting the repository output to the
DataFrame format expected by backtesting and strategy execution.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from datetime import timezone as py_timezone

import pandas as pd
from django.utils import timezone

from .market_data_repository import (
    BrokerError,
    DataIncompleteError,
    DataNotAvailableError,
    get_repository,
)
from .services import MarketDataService

logger = logging.getLogger(__name__)


def _coerce_datetime(value, start_of_day: bool) -> datetime:
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return value.replace(tzinfo=py_timezone.utc)
        return value.astimezone(py_timezone.utc)
    if isinstance(value, date):
        base = datetime.combine(value, time.min if start_of_day else time.max)
        return base.replace(tzinfo=py_timezone.utc)
    raise TypeError(f"Unsupported date value: {value!r}")


class StrategyMarketDataService:
    """
    Shared access layer for strategy consumers (Backtest, Paper, Live).

    Uses ``MarketDataRepository`` for all completeness guarantees.
    Callers receive pandas DataFrames ready for indicator computation.
    """

    @classmethod
    def get_backtest_multi_timeframe_data(
        cls, config, instrument, *, start_dt, end_dt, fetch_missing=True
    ):
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
        base_timeframe = MarketDataService.normalize_timeframe(
            time_rule.get("candle_timeframe", "1m")
        )
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
        symbol: str,
        resolution: str,
        start_dt,
        end_dt,
        fetch_missing: bool = True,
        clean: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch candles for backtesting.

        Uses MarketDataRepository for exact coverage validation and FYERS
        backfill so that backtests never silently run on partial data.

        If the broker returns an error or data cannot be completed, returns an
        empty DataFrame rather than partial data (fail-safe for backtests).
        """
        timeframe = MarketDataService.normalize_timeframe(resolution)
        start_dt = _coerce_datetime(start_dt, start_of_day=True)
        end_dt = _coerce_datetime(end_dt, start_of_day=False)

        repo = get_repository()

        try:
            dict_candles = repo.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                start=start_dt,
                end=end_dt,
                ensure_complete=fetch_missing,
                allow_partial=False,  # backtests must never use partial data
            )
        except DataNotAvailableError as exc:
            logger.info(
                "No data available for %s %s [%s→%s]: %s",
                symbol, timeframe, start_dt.date(), end_dt.date(), exc.reason,
            )
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        except (DataIncompleteError, BrokerError) as exc:
            logger.warning(
                "Data unavailable for backtest %s %s [%s→%s]: %s",
                symbol, timeframe, start_dt.date(), end_dt.date(), exc,
            )
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        except Exception as exc:
            logger.exception(
                "Unexpected error fetching backtest candles for %s %s: %s",
                symbol, timeframe, exc,
            )
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        if not dict_candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(dict_candles)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.drop(columns=["time"])

        if clean:
            return cls.normalize_candles_df(df)
        return df

    @classmethod
    def normalize_candles_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        normalized = df.copy()
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"])
        normalized = normalized.sort_values("timestamp")
        normalized = normalized.drop_duplicates(subset=["timestamp"], keep="last")
        normalized = normalized.set_index("timestamp")
        normalized.index.name = "timestamp"
        return normalized[["open", "high", "low", "close", "volume"]]
