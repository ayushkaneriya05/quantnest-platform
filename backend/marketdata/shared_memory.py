"""
marketdata/shared_memory.py

POSIX shared-memory circular buffer for O(1) live-candle OHLCV data.

CONSISTENCY MODEL — seqlock-style write-side protocol
=====================================================
The meta block stores four values:
  [0] current_index   — circular buffer write pointer  (int64)
  [1] tick_counter    — monotonically increasing count (int64, write-side only)
  [2] write_seq       — ODD while a write is in progress, EVEN when stable (int64)
  [3] prev_cumvol     — previous vol_traded_today seen for this symbol (float64)

Write protocol:
  1. Increment write_seq to ODD (begin-write marker).
  2. Write data.
  3. Increment write_seq to next EVEN (end-write marker).

Read protocol (get_snapshot):
  1. Read write_seq; if odd, spin briefly.
  2. Copy the row.
  3. Re-read write_seq; retry if different.

VOLUME NOTES
============
vol_traded_today from FYERS is the CUMULATIVE daily volume for the symbol.
The delta is computed here, in the SHM writer, once per tick:

    delta = vol_traded_today - prev_cumvol    (stored in meta[3])

If delta < 0 (reconnect / daily reset), it is clamped to 0.
This means:
  - No per-symbol Python dict is needed in FyersLiveFeedClient.
  - Each candle slot's volume field = actual volume traded in that minute.
  - All SHM readers get correct per-minute volume without any extra work.
"""

import time as _time
import numpy as np
from multiprocessing import shared_memory
import logging

logger = logging.getLogger(__name__)

# Meta block layout — all float64 so one dtype handles both int counters and
# the prev_cumvol float.  int counters fit exactly in float64 up to 2^53.
_META_CURRENT_INDEX = 0   # circular buffer write pointer
_META_TICK_COUNTER  = 1   # monotonically increasing tick count
_META_WRITE_SEQ     = 2   # seqlock sequence (ODD = write in progress)
_META_PREV_CUMVOL   = 3   # last vol_traded_today seen (for delta computation)

_META_SLOTS = 4
_META_BYTES = _META_SLOTS * 8  # 4 × float64


class SharedMemoryManager:
    """
    Manages POSIX Shared Memory blocks for Numpy arrays.
    Creates a circular buffer for O(1) appending of OHLCV data.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        max_size: int = 10000,
        create: bool = False,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.max_size = max_size
        self.shape = (max_size, 6)  # Open, High, Low, Close, Volume, epoch timestamp
        self.dtype = np.float64

        # Safe names for POSIX (cannot have special chars)
        safe_sym = symbol.replace(":", "_").replace("-", "_")
        self.data_name = f"data_v2_{safe_sym}_{timeframe}"
        self.meta_name = f"meta_v2_{safe_sym}_{timeframe}"

        self.data_shm = None
        self.meta_shm = None
        self.array = None
        self.meta_array = None

        self._init_memory(create)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_memory(self, create: bool):
        data_bytes = self.max_size * 6 * 8
        meta_bytes = _META_BYTES

        if create:
            try:
                self.data_shm = shared_memory.SharedMemory(
                    name=self.data_name, create=True, size=data_bytes
                )
                self.meta_shm = shared_memory.SharedMemory(
                    name=self.meta_name, create=True, size=meta_bytes
                )
            except FileExistsError:
                self.data_shm = shared_memory.SharedMemory(name=self.data_name)
                self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)
        else:
            try:
                self.data_shm = shared_memory.SharedMemory(name=self.data_name)
                self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)
            except FileNotFoundError:
                logger.error(
                    "Shared memory blocks not found for %s %s", self.symbol, self.timeframe
                )
                raise
            except Exception as e:
                logger.error(
                    "Failed to attach to shared memory for %s %s: %s",
                    self.symbol, self.timeframe, e,
                )
                raise

        # Derive actual capacity from block size (creator may use a different size)
        self.max_size = self.data_shm.size // (6 * 8)
        self.shape = (self.max_size, 6)

        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self.data_shm.buf)
        self.meta_array = np.ndarray((_META_SLOTS,), dtype=np.float64, buffer=self.meta_shm.buf)

        if create:
            self.array.fill(0.0)
            self.meta_array.fill(0.0)

    # ------------------------------------------------------------------
    # Meta accessors
    # ------------------------------------------------------------------

    @property
    def current_index(self) -> int:
        return int(self.meta_array[_META_CURRENT_INDEX])

    @property
    def tick_counter(self) -> int:
        return int(self.meta_array[_META_TICK_COUNTER])

    @property
    def _write_seq(self) -> int:
        return int(self.meta_array[_META_WRITE_SEQ])

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def _begin_write(self):
        """Increment write_seq to an ODD value (in-progress marker)."""
        self.meta_array[_META_WRITE_SEQ] += 1  # ODD

    def _end_write(self):
        """Increment write_seq to the next EVEN value (stable marker)."""
        self.meta_array[_META_WRITE_SEQ] += 1  # EVEN

    def advance_candle(self):
        """Move the write pointer forward when a candle closes."""
        next_idx = (self.current_index + 1) % self.max_size
        self.meta_array[_META_CURRENT_INDEX] = next_idx
        self.array[next_idx].fill(0.0)

    def update_current_candle(
        self,
        price: float,
        cumulative_volume: float,
        timestamp: float = None,
    ):
        """
        Update the forming candle with a new tick.

        Parameters
        ----------
        price             : Last traded price.
        cumulative_volume : vol_traded_today from FYERS (the cumulative daily
                            volume for this symbol/session).  The delta is
                            computed here using the prev_cumvol stored in the
                            meta block, so callers do NOT need to track
                            previous values themselves.
        timestamp         : Unix epoch of the tick (defaults to now).

        Delta computation:
          delta = cumulative_volume - prev_cumvol
          if delta < 0 -> clamped to 0 (handles reconnect / daily reset)
        """
        idx = self.current_index
        tick_timestamp = float(timestamp if timestamp is not None else _time.time())
        candle_timestamp = int(tick_timestamp // 60) * 60

        if self.array[idx, 5] and self.array[idx, 5] != candle_timestamp:
            self._begin_write()
            self.advance_candle()
            idx = self.current_index
            self._end_write()

        # Compute incremental volume from the stored previous cumulative value
        prev_cumvol = float(self.meta_array[_META_PREV_CUMVOL])
        delta = max(0.0, float(cumulative_volume) - prev_cumvol)
        self.meta_array[_META_PREV_CUMVOL] = float(cumulative_volume)

        # --- Seqlock write ---
        self._begin_write()

        if self.array[idx, 0] == 0.0:
            self.array[idx, 0] = price   # open
            self.array[idx, 1] = price   # high
            self.array[idx, 2] = price   # low
            self.array[idx, 3] = price   # close
            self.array[idx, 4] = delta   # volume (incremental)
            self.array[idx, 5] = candle_timestamp
        else:
            if price > self.array[idx, 1]:
                self.array[idx, 1] = price
            if price < self.array[idx, 2]:
                self.array[idx, 2] = price
            self.array[idx, 3] = price
            self.array[idx, 4] += delta
            self.array[idx, 5] = candle_timestamp

        self.meta_array[_META_TICK_COUNTER] += 1
        self._end_write()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_snapshot_row(self, idx: int, max_retries: int = 10) -> np.ndarray:
        """
        Return a consistent copy of row *idx* using the seqlock protocol.

        Spins until the write_seq is EVEN (no write in progress) and
        the sequence does not change across the copy.

        Returns None if a consistent snapshot cannot be obtained within
        *max_retries* attempts.
        """
        for _ in range(max_retries):
            seq_before = int(self.meta_array[_META_WRITE_SEQ])
            if seq_before % 2 != 0:
                # Writer in progress — wait briefly
                _time.sleep(0.0001)
                continue

            snapshot = self.array[idx].copy()

            seq_after = int(self.meta_array[_META_WRITE_SEQ])
            if seq_before == seq_after:
                return snapshot

            # Sequence changed mid-copy — retry
            _time.sleep(0.0001)

        logger.warning("Could not obtain consistent SHM snapshot for %s", self.symbol)
        return None

    def get_latest_data(self, lookback: int = None) -> np.ndarray:
        """
        Retrieve ordered data from the circular buffer.

        Uses get_snapshot_row for the currently-forming candle (most likely
        to be in mid-write).  Historical rows are read without seqlock since
        they are immutable once the pointer advances.
        """
        if lookback is None or lookback > self.max_size:
            lookback = self.max_size

        idx = self.current_index

        # Roll so oldest is at index 0, current (forming) is at the end
        rolled = np.roll(self.array, -(idx + 1), axis=0)

        # Replace the last row (forming candle) with a consistent snapshot
        snapshot = self.get_snapshot_row(idx)
        if snapshot is not None:
            rolled[-1] = snapshot

        return rolled[-lookback:]

    def get_latest_price(self) -> float | None:
        """Return the latest forming candle close price, or None if empty."""
        snapshot = self.get_snapshot_row(self.current_index)
        if snapshot is None or snapshot[0] == 0.0:
            return None
        if not self._validate_price_data(snapshot):
            logger.warning("Invalid price data detected for %s, returning None", self.symbol)
            return None
        return float(snapshot[3])

    @staticmethod
    def _validate_price_data(data_row) -> bool:
        """Basic OHLCV sanity check."""
        try:
            o, h, l, c, v, _ = (float(x) for x in data_row)
            if any(p <= 0 for p in (o, h, l, c)):
                return False
            if h < l:
                return False
            if c > h or c < l:
                return False
            if v < 0:
                return False
            return True
        except (ValueError, TypeError, IndexError):
            return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Release shared-memory handles without destroying the block."""
        if self.data_shm:
            self.data_shm.close()
        if self.meta_shm:
            self.meta_shm.close()

    def unlink(self):
        """Destroy the shared-memory block.  Call only from the creator."""
        self.close()
        if self.data_shm:
            try:
                self.data_shm.unlink()
            except Exception:
                pass
        if self.meta_shm:
            try:
                self.meta_shm.unlink()
            except Exception:
                pass

    def preload_historical_data(self, max_lookback: int):
        """
        Preload historical candles into the circular buffer from DB / FYERS.

        Always fetches from FYERS first if the DB data is stale so that SHM
        starts with the most recent available data.
        """
        from marketdata.services import MarketDataService
        from django.utils import timezone
        from datetime import timedelta

        try:
            latest_candle = MarketDataService.latest_candle(self.symbol, self.timeframe)
            needs_fyers_fetch = False

            if latest_candle:
                age_minutes = (timezone.now() - latest_candle.time).total_seconds() / 60
                if age_minutes > 5:
                    needs_fyers_fetch = True
                    logger.info(
                        "DB data for %s is %.1f min old — fetching from Fyers",
                        self.symbol, age_minutes,
                    )
            else:
                needs_fyers_fetch = True
                logger.info("No DB data for %s — fetching from Fyers", self.symbol)

            if needs_fyers_fetch:
                end_dt = timezone.now()
                start_dt = end_dt - timedelta(days=7)
                fetched = MarketDataService.backfill_candles_from_broker(
                    symbol=self.symbol,
                    date_from=start_dt.isoformat(),
                    date_to=end_dt.isoformat(),
                    timeframe=self.timeframe,
                )
                if fetched:
                    logger.info(
                        "Fetched %d candles from Fyers for %s", len(fetched), self.symbol
                    )

            candles = MarketDataService.list_candles(
                symbol=self.symbol, timeframe=self.timeframe, limit=max_lookback
            )

            if not candles:
                logger.warning(
                    "No historical candles found for %s %s to preload.",
                    self.symbol, self.timeframe,
                )
                self.array.fill(0.0)
                self.meta_array.fill(0)
                return

            logger.info(
                "Preloading %d historical candles for %s %s into SHM.",
                len(candles), self.symbol, self.timeframe,
            )

            self.array.fill(0.0)
            self.meta_array.fill(0)

            for i, candle in enumerate(candles):
                idx = self.current_index
                is_dict = isinstance(candle, dict)

                c_open = candle.get("open", 0.0) if is_dict else float(getattr(candle, "open", 0.0))
                c_high = candle.get("high", 0.0) if is_dict else float(getattr(candle, "high", 0.0))
                c_low = candle.get("low", 0.0) if is_dict else float(getattr(candle, "low", 0.0))
                c_close = candle.get("close", 0.0) if is_dict else float(getattr(candle, "close", 0.0))
                c_volume = candle.get("volume", 0.0) if is_dict else float(getattr(candle, "volume", 0.0))
                candle_time = candle.get("time", 0.0) if is_dict else getattr(candle, "time", 0.0)
                if hasattr(candle_time, "timestamp"):
                    candle_time = candle_time.timestamp()

                self.array[idx, 0] = float(c_open)
                self.array[idx, 1] = float(c_high)
                self.array[idx, 2] = float(c_low)
                self.array[idx, 3] = float(c_close)
                self.array[idx, 4] = float(c_volume)
                self.array[idx, 5] = float(candle_time or 0.0)

                if i < len(candles) - 1:
                    self.advance_candle()

            logger.info(
                "Successfully preloaded %d candles for %s %s.",
                len(candles), self.symbol, self.timeframe,
            )
        except Exception as e:
            logger.exception("Failed to preload historical data for %s: %s", self.symbol, e)
