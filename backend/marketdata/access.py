from decimal import Decimal

from .services import FyersDataService, MarketDataService
from .streaming import MarketDataStreamer


class StrategyMarketDataService:
    """
    Shared access layer for strategy consumers.

    This keeps paper/live/backtest execution code away from the lower-level
    marketdata cache and storage details.
    """

    @classmethod
    def get_quote(cls, instrument, fallback_price=None):
        quote = None
        if instrument is not None:
            quote = (
                MarketDataStreamer.get_cached_quote(instrument.sym_ticker)
                or MarketDataStreamer.poll_latest_candle_quote(instrument.sym_ticker)
            )
        if quote and quote.get("price") is not None:
            return Decimal(str(quote["price"]))
        if fallback_price is not None:
            return Decimal(str(fallback_price))
        if instrument is not None and instrument.previous_close is not None:
            return Decimal(str(instrument.previous_close))
        raise ValueError("Live market price is unavailable")

    @classmethod
    def get_multi_timeframe_data(cls, config, instrument, *, lookback_days=30, fetch_missing=True, candle_state=None):
        if instrument is None:
            return None, {}

        from rules_engine.metadata import IndicatorRequirementAnalyzer
        from .candle_engine import LiveCandleStore

        base_timeframe, required_timeframes = cls.required_timeframes(config)
        warmup_reqs = IndicatorRequirementAnalyzer.get_warmup_requirements(config)

        mtf_data = {}
        for timeframe in required_timeframes:
            max_lookback = warmup_reqs.get(timeframe, IndicatorRequirementAnalyzer.MIN_LOOKBACK)
            # Fetch directly from the ultra-fast bounded ring buffer
            df = LiveCandleStore.get_candle_df(instrument.sym_ticker, timeframe, max_lookback=max_lookback, candle_state=candle_state)
            if df is not None and not df.empty:
                mtf_data[timeframe] = df

        return base_timeframe, mtf_data

    @classmethod
    def get_backtest_multi_timeframe_data(cls, config, instrument, *, start_dt, end_dt, fetch_missing=True):
        if instrument is None:
            return None, {}

        base_timeframe, required_timeframes = cls.required_timeframes(config)
        mtf_data = {}
        for timeframe in required_timeframes:
            df = FyersDataService.get_backtest_candles(
                symbol=instrument.sym_ticker,
                resolution=timeframe,
                start_dt=start_dt,
                end_dt=end_dt,
                fetch_missing=fetch_missing,
                clean=True,
                persist=True,
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
            for collection_name in ("rules", "stop_loss_rules", "target_rules"):
                for rule in group.get(collection_name, []) or []:
                    timeframe_override = rule.get("timeframe_override")
                    if timeframe_override:
                        required_timeframes.add(MarketDataService.normalize_timeframe(timeframe_override))
        return base_timeframe, required_timeframes
