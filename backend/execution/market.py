"""Prepare shared features once, then advance them with local market observations."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from django.db import close_old_connections

from common.enums import CandleTimeframe
from marketdata.candles import aggregate_candles, candle_frame
from marketdata.contracts import OHLCV, source_timeframe
from marketdata.shared_memory import SharedMemoryManager

from .compiler import CandleHistoryConflict, FeatureGraph, Program
from .types import Candle, Tick


@dataclass(slots=True)
class PreparedSymbol:
    symbol: str
    graph: FeatureGraph
    forming: dict[str, Candle]
    cursor: int
    generation: int
    revisions: dict[str, int]
    prepared_at: datetime


def prepare_symbol(symbol: str, programs: list[Program]) -> PreparedSymbol:
    """Keep ORM connections local to the controller's preparation thread."""
    close_old_connections()
    try:
        return _prepare_symbol(symbol, programs)
    finally:
        close_old_connections()


def _prepare_symbol(symbol: str, programs: list[Program]) -> PreparedSymbol:
    """Background preparation only: batch frames are discarded after node warmup."""
    if not programs:
        raise ValueError('Feature preparation needs at least one strategy program.')
    calendar = programs[0].calendar
    depths, timeframes = {}, set()
    for program in programs:
        timeframes.update(program.counts)
        for source, count in program.sources.items():
            depths[source] = max(depths.get(source, 0), count)
    from marketdata.live_feed import LiveMarketDataRegistry
    if not LiveMarketDataRegistry.is_ready(symbol, depths, LiveMarketDataRegistry.get_state()):
        raise ValueError('Waiting for confirmed subscriptions and prepared market history.')
    # A running daily/weekly candle also needs today's completed minute history.
    if CandleTimeframe.D1 in depths:
        depths[CandleTimeframe.M1] = max(depths.get(CandleTimeframe.M1, 0), calendar.session_minutes + 2)
    buffers = {}
    try:
        for source in depths:
            buffers[source] = SharedMemoryManager(symbol, source)
        snapshots = {source: buffer.snapshot(depths[source]) for source, buffer in buffers.items()}
        now = datetime.fromtimestamp(snapshots[CandleTimeframe.M1].captured_at, timezone.utc)
        sources = {source: candle_frame([dict(zip((*OHLCV, 'time'), row)) for row in snapshot.rows
                                        if row[0] > 0 and row[5] > 0])
                   for source, snapshot in snapshots.items()}
        # The daily buffer can contain today's forming row. Today's minute
        # history below is its only source, so volume is not counted twice.
        if CandleTimeframe.D1 in sources:
            frame = sources[CandleTimeframe.D1]
            sources[CandleTimeframe.D1] = frame.loc[[calendar.candle_close(at, CandleTimeframe.D1) <= now for at in frame.index]]
        earliest = min(frame.index[0].date() for frame in sources.values() if not frame.empty)
        calendar.load_holidays(earliest, now.astimezone(calendar.zone).date() + timedelta(days=31))
        graph = FeatureGraph(calendar, capacity=max(max(program.counts.values()) for program in programs) + 256)
        for program in programs:
            graph.register(program)
        forming = {}
        for tf in timeframes:
            source = source_timeframe(tf)
            frame = aggregate_candles(sources[source], tf, calendar, now, source=source, include_open=True)
            for row in frame.iloc[1:].itertuples():
                candle = Candle(row.Index.to_pydatetime(), calendar.candle_close(row.Index, tf),
                    row.open, row.high, row.low, row.close, row.volume)
                if candle.closed_at <= now:
                    graph.append(tf, candle)
                else:
                    forming[tf] = candle
            if source == CandleTimeframe.D1:
                # Daily provider rows end before today's active session. Aggregate
                # the observed minutes into the open day/week, without double volume.
                minute_frame = sources[CandleTimeframe.M1]
                today = calendar.session_bounds(now)[0]
                partial = aggregate_candles(minute_frame.loc[minute_frame.index >= today], tf, calendar, now,
                                            source=CandleTimeframe.M1, include_open=True)
                for row in partial.itertuples():
                    end = calendar.candle_close(row.Index, tf)
                    if end <= now:
                        continue
                    item = Candle(row.Index.to_pydatetime(), end, row.open, row.high, row.low, row.close, row.volume)
                    old = forming.get(tf)
                    forming[tf] = combine(old, item) if old and old.opened_at == item.opened_at else item
        minute = snapshots[CandleTimeframe.M1]
        return PreparedSymbol(symbol, graph, forming, minute.sequence, minute.generation,
                              {tf: snapshot.history_revision for tf, snapshot in snapshots.items()}, now)
    finally:
        for buffer in buffers.values():
            buffer.close()


def combine(previous: Candle, current: Candle) -> Candle:
    return replace(previous, high=max(previous.high, current.high), low=min(previous.low, current.low),
                   close=current.close, volume=previous.volume+current.volume)


def complete(symbol: PreparedSymbol, at: datetime) -> bool:
    """Close observed buckets on the clock even when the next tick is quiet."""
    changed = False
    for tf, candle in tuple(symbol.forming.items()):
        if candle.closed_at <= at:
            symbol.graph.append(tf, candle)
            del symbol.forming[tf]
            changed = True
    return changed


def observe(symbol: PreparedSymbol, tick: Tick) -> None:
    calendar = symbol.graph.calendar
    if not calendar.is_open(tick.event_time):
        complete(symbol, tick.event_time)
        return
    # The clock (or startup snapshot) can close a bucket before its final tick
    # reaches us. Never reopen it or update recursive indicators twice. SHM
    # already contains this tick; background preparation rebuilds its features.
    candles = {}
    for tf in symbol.graph.counts:
        opened = calendar.bucket_start(tick.event_time, tf)
        closed = calendar.candle_close(opened, tf)
        completed = symbol.graph.completed.get(tf)
        if completed is not None and closed <= completed:
            raise CandleHistoryConflict(f'Late tick changed completed {tf} history for {symbol.symbol}.')
        candles[tf] = Candle(opened, closed, tick.price, tick.price, tick.price, tick.price, tick.volume)
    # Validate all timeframes before modifying any of their forming candles.
    complete(symbol, tick.event_time)
    for tf, current in candles.items():
        previous = symbol.forming.get(tf)
        symbol.forming[tf] = combine(previous, current) if previous else current
