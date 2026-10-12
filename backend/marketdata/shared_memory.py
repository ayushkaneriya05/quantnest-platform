
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
from pathlib import Path

import numpy as np

HEADER = 128
TICK_COLUMNS = 5  # sequence, event epoch, receive epoch, price, volume delta


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
                tick_capacity = max(1024, int(os.environ.get("MARKET_TICK_CAPACITY", "32768")))
                size = HEADER + capacity * 6 * 8 + tick_capacity * TICK_COLUMNS * 8
                self._file.truncate(size)
                self._file.seek(0)
                self._file.write(struct.pack("<qq", capacity, tick_capacity))
                self._file.flush()
            self._map = mmap.mmap(self._file.fileno(), size)
            self.max_size, self.tick_capacity = struct.unpack_from("<qq", self._map)
            if self.max_size < 2 or size != HEADER + self.max_size * 48 + self.tick_capacity * TICK_COLUMNS * 8:
                raise ValueError("Invalid market buffer header")
            self.meta_array = np.ndarray((8,), dtype=np.int64, buffer=self._map, offset=16)
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

    @property
    def revision(self):
        with self._locked(shared=True):
            return int(self.meta_array[3])

    def is_tick_fresh(self, max_age_seconds=15.0):
        with self._locked(shared=True):
            received = int(self.meta_array[2]) / 1000.0
        return received > 0 and 0 <= time.time() - received <= max_age_seconds

    @property
    def history_revision(self):
        with self._locked(shared=True):
            return int(self.meta_array[4])

    def advance_candle(self):
        with self._locked():
            index = (int(self.meta_array[0]) + 1) % self.max_size
            self.array[index].fill(0)
            self.meta_array[0] = index
            self.meta_array[3] += 1

    @property
    def source_gap(self):
        with self._locked(shared=True):
            return int(self.meta_array[5])

    def mark_gap(self):
        with self._locked():
            self.meta_array[5] += 1

    def update_current_candle(self, price, volume, timestamp=None, received_time=None,
                              source_sequence=None, source_generation=None):
        price, volume = float(price), float(volume)
        event_time = float(timestamp if timestamp is not None else time.time())
        if not np.isfinite([price, volume, event_time]).all() or price <= 0 or volume < 0:
            raise ValueError("Invalid normalized market tick")
        received = float(received_time if received_time is not None else time.time())
        if not np.isfinite(received) or received <= 0 or received > time.time() + 1:
            raise ValueError("Invalid market receipt timestamp")
        candle_time = int(event_time // 60) * 60
        with self._locked():
            if source_sequence is not None:
                previous_sequence, previous_generation = int(self.meta_array[6]), int(self.meta_array[7])
                if previous_generation == source_generation and previous_sequence >= source_sequence:
                    return False
                if previous_sequence and (previous_generation != source_generation or source_sequence != previous_sequence + 1):
                    self.meta_array[5] += 1
                self.meta_array[6], self.meta_array[7] = source_sequence, source_generation
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
            sequence = int(self.meta_array[1]) + 1
            self.ticks[(sequence - 1) % self.tick_capacity] = [sequence, event_time, received, price, volume]
            self.meta_array[2] = int(received * 1000)
            self.meta_array[1] = sequence
        return sequence

    def read_ticks(self, after_sequence, limit=None):
        with self._locked(shared=True):
            latest = int(self.meta_array[1])
            oldest = max(1, latest - self.tick_capacity + 1)
            gap = after_sequence > latest or after_sequence + 1 < oldest
            first = max(oldest, after_sequence + 1) if after_sequence <= latest else oldest
            end = min(latest + 1, first + int(limit)) if limit else latest + 1
            indices = (np.arange(first, end, dtype=np.int64) - 1) % self.tick_capacity
            return self.ticks[indices].copy(), gap

    def get_latest_data(self, lookback=None):
        with self._locked(shared=True):
            count = self.max_size if lookback is None else min(self.max_size, max(0, int(lookback)))
            index = int(self.meta_array[0])
            indices = (np.arange(index - count + 1, index + 1) % self.max_size).astype(int)
            return self.array[indices].copy()

    def get_latest_price(self):
        with self._locked(shared=True):
            row = self.array[int(self.meta_array[0])].copy()
        return float(row[3]) if self._validate_price_data(row) else None

    @staticmethod
    def _validate_price_data(row):
        return bool(np.isfinite(row).all() and min(row[:4]) > 0 and row[1] >= row[2]
                    and row[2] <= row[3] <= row[1] and row[4] >= 0 and row[5] > 0)

    def preload_historical_data(self, max_lookback, validate=True):
        from marketdata.services import MarketDataService
        if max_lookback > self.max_size:
            raise ValueError("Historical depth exceeds buffer capacity")
        if validate:
            readiness = MarketDataService.ensure_historical_candles(self.symbol, self.timeframe, max_lookback)
            if not readiness["ready"]:
                raise ValueError(f"Historical data incomplete for {self.symbol}")
        candles = MarketDataService.list_candles(self.symbol, self.timeframe, limit=max_lookback)
        if len(candles) < max_lookback:
            raise ValueError(f"Historical depth incomplete for {self.symbol}")
        rows = []
        for candle in candles:
            epoch = candle["time"]
            epoch = epoch.timestamp() if hasattr(epoch, "timestamp") else epoch
            row = [candle[key] for key in ("open", "high", "low", "close", "volume")] + [epoch]
            if not self._validate_price_data(np.asarray(row, dtype=float)):
                raise ValueError(f"Invalid historical candle for {self.symbol}")
            rows.append(row)
        with self._locked():
            current = self.array[int(self.meta_array[0])].copy()
            if current[5] and current[5] > rows[-1][5]:
                rows.append(current.tolist())
            elif current[5] and current[5] == rows[-1][5] and self.is_tick_fresh():
                rows[-1] = current.tolist()
            rows = rows[-self.max_size:]
            self.array.fill(0)
            self.array[:len(rows)] = rows
            self.meta_array[0] = len(rows) - 1
            self.meta_array[3] += 1
            self.meta_array[4] += 1
            # Preserve tick sequence and receipt time: history is not a fresh quote.

    def close(self):
        self.array = self.ticks = self.meta_array = None
        self._map.close()
        self._file.close()

    def unlink(self):
        self.close()
        self.path.unlink(missing_ok=True)
