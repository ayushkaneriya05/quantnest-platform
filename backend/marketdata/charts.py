"""Chart orchestration over the common reader; history acquisition is bounded."""
import json
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from django.utils import timezone as django_timezone

from common.enums import ChartTimeframe
from common.redis import runtime_redis
from instruments.models import Instrument
from .calendar import MarketSessionCalendar
from .candles import read_candles, read_source_data, candle_frame, aggregate_candles
from .contracts import CandleRequest, HistoryRequest, OHLCV, interval_minutes, source_timeframe
from .history import completed_request, ensure_history, missing_history, data_revision

INTERVALS = ChartTimeframe.values


class ChartDataService:
    @classmethod
    def chart_window(cls, symbol, resolution=ChartTimeframe.M1, limit=300, before=None, *, fetch_missing=False):
        instrument = Instrument.objects.get(sym_ticker=symbol)
        calendar = MarketSessionCalendar.for_instrument(instrument)
        minutes = interval_minutes(resolution)
        limit = max(1, min(int(limit), 1000))
        now = django_timezone.now()
        end = datetime.fromtimestamp(float(before), timezone.utc) if before is not None else now
        if instrument.expiry_date:
            end = min(end, calendar.session_close(instrument.expiry_date))
        days = (max(7, int(limit * minutes / calendar.session_minutes * 2.2) + 7) if minutes else
                int(limit * {ChartTimeframe.D1: 1.6, ChartTimeframe.W1: 8, ChartTimeframe.MN1: 32}[resolution]) + 7)
        calendar.load_holidays((end - timedelta(days=days + 7)).astimezone(calendar.zone).date(),
                               max(now, end).astimezone(calendar.zone).date() + timedelta(days=31))
        if minutes:
            first = calendar.warmup_start(end, (limit + 1) * minutes, source="1m").date()
            start = calendar.session_open(first).astimezone(timezone.utc)
        else:
            start = calendar.bucket_start(end - timedelta(days=days), resolution).astimezone(timezone.utc)
        request = CandleRequest(instrument, resolution, start, end, calendar, limit + 1, include_open=True)
        batch = read_candles(request)
        rows = batch.records()
        history_start = datetime.fromtimestamp(rows[-limit]["time"], timezone.utc) if len(rows) >= limit else start
        history = completed_request(HistoryRequest(instrument, source_timeframe(resolution), history_start, end, calendar))
        gaps = missing_history(history)
        error, fetched, attempted = "", 0, False
        if fetch_missing and gaps:
            result = ensure_history(history, max_requests=1)
            error, fetched, attempted = result.error, result.fetched, result.requests > 0
            if result.changed:
                batch = read_candles(request)
                rows = batch.records()
            gaps = result.missing
        more = len(rows) > limit or bool(gaps)
        rows = rows[-limit:]
        if before is None:
            cached = runtime_redis().get(f"quantnest:chart-live:{symbol}:{resolution}")
            if cached:
                live = json.loads(cached)
                if live["data_revision"] == data_revision(symbol) and (
                        not rows or live["time"] > rows[-1]["time"]
                        or live["time"] == rows[-1]["time"] and live["revision"] >= rows[-1]["revision"]):
                    rows = [row for row in rows if row["time"] < live["time"]] + [live]
                    rows = rows[-limit:]
        transitions = [boundary.timestamp() for offset in range(15)
                       for left, right in calendar.trading_periods(now.astimezone(calendar.zone).date() + timedelta(days=offset))
                       for boundary in (left, right) if boundary > now]
        opening, closing = calendar.session_bounds(now)
        return {
            "symbol": symbol, "interval": resolution, "candles": rows,
            "pagination": {"has_more": more or len(rows) >= limit,
                           "next_before": rows[0]["time"] if rows else int(start.timestamp())},
            "source": {"database_count": len(batch.frame), "fetched_count": fetched, "fetch_attempted": attempted},
            "backfill_requested": bool(gaps) and not bool(error), "history_error": error,
            "data_revision": batch.quality["revision"],
            "session": {"timezone": calendar.timezone_name, "open": opening.timestamp(), "close": closing.timestamp(),
                        "is_open": calendar.is_open(now), "next_transition": min(transitions) if transitions else None},
            "active_bucket": int(calendar.bucket_start(now, resolution).timestamp()), "intervals": INTERVALS,
        }


class LiveChartPublisher:
    """Prepare shared history once per source minute; publish the active bar cheaply."""
    def __init__(self):
        self.subscriptions, self.calendars, self.prefixes = {}, {}, {}
        self.last_refresh = 0

    def _refresh_subscriptions(self):
        """Drop expired browser demand and release caches for closed charts."""
        now = time.monotonic()
        if now - self.last_refresh < 1:
            return
        redis = runtime_redis()
        redis.zremrangebyscore("quantnest:chart-subscriptions", "-inf", time.time() - 75)
        self.subscriptions = {}
        for value in redis.zrange("quantnest:chart-subscriptions", 0, -1):
            symbol, interval, _ = json.loads(value)
            self.subscriptions.setdefault(symbol, set()).add(interval)
        self.calendars = {symbol: value for symbol, value in self.calendars.items() if symbol in self.subscriptions}
        self.prefixes = {symbol: value for symbol, value in self.prefixes.items() if symbol in self.subscriptions}
        self.last_refresh = now

    @staticmethod
    def _prepare_prefixes(instrument, calendar, starts, instant, observations):
        """Share one minute read and at most one daily read across all chart intervals."""
        daily_intervals = {interval for interval in starts if source_timeframe(interval) == ChartTimeframe.D1}
        session_open = calendar.session_bounds(instant)[0]
        first = min(session_open if interval in daily_intervals else start for interval, start in starts.items())
        minutes, _ = read_source_data(completed_request(
            HistoryRequest(instrument, ChartTimeframe.M1, first, instant, calendar)))
        observed = candle_frame([dict(zip((*OHLCV, "time"), row)) for row in observations
                                if first.timestamp() <= row[5] < instant.timestamp() and row[0] > 0])
        # Provider corrections win over observations at the same source timestamp.
        sources = {ChartTimeframe.M1: minutes.combine_first(observed).sort_index()}
        if daily_intervals:
            days = aggregate_candles(sources[ChartTimeframe.M1], ChartTimeframe.D1, calendar,
                                     instant, include_open=True).loc[:, list(OHLCV)]
            first_day = min(starts[interval] for interval in daily_intervals)
            if first_day < session_open:
                stored, _ = read_source_data(completed_request(
                    HistoryRequest(instrument, ChartTimeframe.D1, first_day, session_open, calendar)))
                days = stored.combine_first(days).sort_index()
            sources[ChartTimeframe.D1] = days
        prefixes = {}
        for interval, start in starts.items():
            source = source_timeframe(interval)
            frame = aggregate_candles(sources[source], interval, calendar, instant, source=source, include_open=True)
            rows = frame.loc[frame.index == pd.Timestamp(start)]
            prefixes[interval] = rows.iloc[-1].to_dict() if not rows.empty else None
        return prefixes

    def publish(self, symbol, read_observations):
        from .streaming import MarketDataStreamer
        self._refresh_subscriptions()
        if symbol not in self.subscriptions:
            return
        latest = read_observations(symbol, 1)
        if not len(latest) or latest[-1][5] <= 0:
            return
        raw = latest[-1]
        instant = datetime.fromtimestamp(raw[5], timezone.utc)
        if symbol not in self.calendars or time.monotonic() - self.calendars[symbol][0] >= 60:
            instrument = Instrument.objects.get(sym_ticker=symbol)
            calendar = MarketSessionCalendar.for_instrument(instrument)
            calendar.load_holidays(instant.astimezone(calendar.zone).date() - timedelta(days=40),
                                   instant.astimezone(calendar.zone).date() + timedelta(days=31))
            self.calendars[symbol] = time.monotonic(), instrument, calendar
        _, instrument, calendar = self.calendars[symbol]
        if not calendar.is_open(instant):
            return
        revision = data_revision(symbol)
        starts = {interval: calendar.bucket_start(instant, interval) for interval in self.subscriptions[symbol]}
        marker = int(raw[5]), revision, calendar.signature, tuple(sorted(starts))
        if symbol not in self.prefixes or self.prefixes[symbol][0] != marker:
            self.prefixes[symbol] = marker, self._prepare_prefixes(
                instrument, calendar, starts, instant, read_observations(symbol, 0))
        redis = runtime_redis()
        for interval, start in starts.items():
            prefix = self.prefixes[symbol][1][interval]
            candle = {
                "time": int(start.timestamp()), "open": float(prefix["open"]) if prefix else float(raw[0]),
                "high": max(float(prefix["high"]), float(raw[1])) if prefix else float(raw[1]),
                "low": min(float(prefix["low"]), float(raw[2])) if prefix else float(raw[2]),
                "close": float(raw[3]), "volume": int(prefix["volume"] if prefix else 0) + int(raw[4]),
                "revision": time.time(), "data_revision": revision, "source": "observed", "is_final": False,
                "source_end": int(raw[5]), "available_at": int(calendar.candle_close(start, interval).timestamp()),
            }
            MarketDataStreamer.publish(MarketDataStreamer.chart_group(symbol, interval), {
                "type": "chart.candle", "symbol": symbol, "interval": interval,
                "candle": {key: candle[key] for key in ("time", *OHLCV, "revision")}})
            redis.set(f"quantnest:chart-live:{symbol}:{interval}", json.dumps(candle), ex=90)
