
"""Consistent, local memory-mapped candles and sequenced observed ticks.

Only the supervised feed writes. Readers take an OS shared lock on Linux;
Windows uses a short exclusive file lock. Publication metadata is updated last.
"""
import hashlib
import mmap
import os
import struct
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from common.enums import CandleTimeframe

HEADER = 128
TICK_COLUMNS = 5  # sequence, event epoch, receive epoch, price, volume delta


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    rows: np.ndarray
    sequence: int
    history_revision: int
    generation: int
    captured_at: float


class SharedMemoryManager:
    def __init__(self, symbol, timeframe, max_size=10000, create=False):
        self.symbol, self.timeframe = symbol, timeframe
        directory = Path(os.environ.get("QUANTNEST_RUNTIME_DIR", str(Path(tempfile.gettempdir()) / "quantnest-runtime")))
        directory.mkdir(parents=True, exist_ok=True)
        identity = hashlib.sha256(f"{symbol}:{timeframe}".encode()).hexdigest()[:32]
        self.path = directory / f"market-v4-{identity}.mmap"
        self._thread_lock = threading.RLock()
        self._depth = 0
        if create:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
            self._file = os.fdopen(descriptor, "r+b")
        else:
            self._file = open(self.path, "r+b")
        with self._locked():
            size = os.fstat(self._file.fileno()).st_size
            if not size:
                if not create:
                    raise FileNotFoundError(self.path)
                capacity = max(2, int(max_size))
                tick_capacity = (max(1024, int(os.environ.get("MARKET_TICK_CAPACITY", "32768")))
                                 if timeframe == "1m" else 0)
                size = HEADER + capacity * 6 * 8 + tick_capacity * TICK_COLUMNS * 8
                self._file.truncate(size)
                self._file.seek(0)
                self._file.write(struct.pack("<qq", capacity, tick_capacity))
                self._file.flush()
            self._map = mmap.mmap(self._file.fileno(), size)
            self.max_size, self.tick_capacity = struct.unpack_from("<qq", self._map)
            if self.max_size < 2 or size != HEADER + self.max_size * 48 + self.tick_capacity * TICK_COLUMNS * 8:
                raise ValueError("Invalid market buffer header")
            # Slot 3 is reserved to retain the existing on-disk buffer layout.
            self.meta_array = np.ndarray((6,), dtype=np.int64, buffer=self._map, offset=16)
            self.array = np.ndarray((self.max_size, 6), dtype=np.float64, buffer=self._map, offset=HEADER)
            self.ticks = np.ndarray((self.tick_capacity, TICK_COLUMNS), dtype=np.float64,
                                    buffer=self._map, offset=HEADER + self.max_size * 48)

    @contextmanager
    def _locked(self, shared=False):
        with self._thread_lock:
            if self._depth == 0:
                if os.name == "nt":
                    import msvcrt
                    self._file.seek(0)
                    deadline = time.monotonic() + 2
                    while True:
                        try:
                            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                            break
                        except OSError:
                            if time.monotonic() >= deadline:
                                raise TimeoutError("Market buffer lock timeout")
                            time.sleep(0.001)
                else:
                    import fcntl
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
                if self._depth == 0:
                    if os.name == "nt":
                        import msvcrt
                        self._file.seek(0)
                        msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)


    @property
    def tick_counter(self):
        with self._locked(shared=True):
            return int(self.meta_array[1])

    def advance_candle(self):
        with self._locked():
            index = (int(self.meta_array[0]) + 1) % self.max_size
            self.array[index].fill(0)
            self.meta_array[0] = index

    @property
    def source_gap(self):
        with self._locked(shared=True):
            return int(self.meta_array[5])

    def mark_gap(self):
        with self._locked():
            self.meta_array[5] += 1
            # Retain chart history, but execution needs a new observed tick.
            self.meta_array[2] = 0

    def update_current_candle(self, price, volume, timestamp=None, received_time=None):
        if self.timeframe != CandleTimeframe.M1:
            raise ValueError("Only the minute observation buffer accepts ticks.")
        price, volume = float(price), float(volume)
        event_time = float(timestamp if timestamp is not None else time.time())
        if not np.isfinite([price, volume, event_time]).all() or price <= 0 or volume < 0 or event_time <= 0:
            raise ValueError("Invalid normalized market tick")
        received = float(received_time if received_time is not None else time.time())
        if not np.isfinite(received) or received <= 0 or received > time.time() + 1 or event_time > received + 1:
            raise ValueError("Invalid market receipt timestamp")
        candle_time = int(event_time // 60) * 60
        with self._locked():
            sequence = int(self.meta_array[1])
            # Late packets must not rewind the live price or evaluate old signals.
            if sequence and event_time < self.ticks[(sequence - 1) % self.tick_capacity, 1]:
                return False
            index = int(self.meta_array[0])
            active = self.array[index, 5]
            if active and candle_time < active:
                return False
            if active and active != candle_time:
                self.advance_candle()
                index = int(self.meta_array[0])
            row = self.array[index]
            if row[0] == 0:
                row[:] = [price, price, price, price, volume, candle_time]
            else:
                row[1], row[2], row[3] = max(row[1], price), min(row[2], price), price
                row[4] += volume
            sequence += 1
            self.ticks[(sequence - 1) % self.tick_capacity] = [sequence, event_time, received, price, volume]
            self.meta_array[2] = int(received * 1000)
            self.meta_array[1] = sequence
        return sequence

    def get_latest_data(self, lookback=None):
        with self._locked(shared=True):
            count = self.max_size if lookback is None else min(self.max_size, max(0, int(lookback)))
            index = int(self.meta_array[0])
            indices = (np.arange(index - count + 1, index + 1) % self.max_size).astype(int)
            return self.array[indices].copy()

    def snapshot(self, lookback: int) -> MarketSnapshot:
        """Warmup candles and their observation cursor must describe one publication."""
        with self._locked(shared=True):
            return MarketSnapshot(self.get_latest_data(lookback), int(self.meta_array[1]),
                                  int(self.meta_array[4]), int(self.meta_array[5]), time.time())

    def read_observations(self, after_sequence: int, limit: int):
        """Read a bounded tick batch and generation under the same publication lock."""
        with self._locked(shared=True):
            latest = int(self.meta_array[1])
            oldest = max(1, latest - self.tick_capacity + 1)
            lost = after_sequence > latest or after_sequence + 1 < oldest
            first = max(oldest, after_sequence + 1) if after_sequence <= latest else oldest
            end = min(latest + 1, first + limit)
            indices = (np.arange(first, end, dtype=np.int64) - 1) % self.tick_capacity
            return self.ticks[indices].copy(), lost, int(self.meta_array[4]), int(self.meta_array[5])

    def get_latest_price(self):
        """Read the latest observation since connection, never a warmup candle."""
        with self._locked(shared=True):
            sequence = int(self.meta_array[1])
            if not sequence or not self.meta_array[2]:
                return None
            tick = self.ticks[(sequence - 1) % self.tick_capacity]
            return float(tick[3])

    def replace_history(self, rows: np.ndarray):
        """Publish prepared OHLCV/time arrays. This storage class performs no service I/O."""
        if not len(rows):
            return
        if rows.ndim != 2 or rows.shape[1] != 6 or len(rows) > self.max_size:
            raise ValueError("Historical data exceeds the buffer shape or capacity.")
        with self._locked():
            tail = self.get_latest_data()
            observed = tail[(tail[:, 5] > rows[-1, 5]) & (tail[:, 0] > 0)]
            combined = np.concatenate((rows, observed))[-self.max_size:]
            self.array.fill(0)
            self.array[:len(combined)] = combined
            self.meta_array[0] = len(combined) - 1
            self.meta_array[4] += 1
            # History never changes observation sequence or connection validity.

    def close(self):
        self.array = self.ticks = self.meta_array = None
        self._map.close()
        self._file.close()

    def unlink(self):
        self.close()
        self.path.unlink(missing_ok=True)


def get_market_price(symbol):
    """Read the latest local observation independently of UI publication."""
    try:
        market = SharedMemoryManager(symbol, CandleTimeframe.M1)
    except FileNotFoundError:
        return None
    try:
        return market.get_latest_price()
    finally:
        market.close()
