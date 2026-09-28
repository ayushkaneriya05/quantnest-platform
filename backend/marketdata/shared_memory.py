import time
import numpy as np
from multiprocessing import shared_memory
import logging

logger = logging.getLogger(__name__)

class SharedMemoryManager:
    """
    Manages POSIX Shared Memory blocks for Numpy arrays.
    Creates a circular buffer for O(1) appending of OHLCV data.
    """
    def __init__(self, symbol: str, timeframe: str, max_size: int = 10000, create: bool = False):
        self.symbol = symbol
        self.timeframe = timeframe
        self.max_size = max_size
        self.shape = (max_size, 6) # Open, High, Low, Close, Volume, epoch timestamp
        self.dtype = np.float64
        
        # Safe names for POSIX (can't have special chars)
        safe_sym = symbol.replace(":", "_").replace("-", "_")
        self.data_name = f"data_v3_{safe_sym}_{timeframe}"
        self.meta_name = f"meta_v3_{safe_sym}_{timeframe}"
        
        self.data_shm = None
        self.meta_shm = None
        self.array = None
        self.meta_array = None
        
        self._init_memory(create)

    def _init_memory(self, create: bool):
        # Data block: max_size * 6 * 8 bytes (float64)
        data_bytes = self.max_size * 6 * 8
        # Meta block: [current_index, tick_counter, latest_tick_epoch_ms]
        meta_bytes = 24
        
        initialized_here = False
        if create:
            try:
                self.data_shm = shared_memory.SharedMemory(name=self.data_name, create=True, size=data_bytes)
                try:
                    self.meta_shm = shared_memory.SharedMemory(name=self.meta_name, create=True, size=meta_bytes)
                except Exception:
                    self.data_shm.close()
                    self.data_shm.unlink()
                    raise
                initialized_here = True
            except FileExistsError:
                # A concurrent feed process may still be creating the paired block.
                deadline = time.monotonic() + 5
                while True:
                    try:
                        self.data_shm = shared_memory.SharedMemory(name=self.data_name)
                        self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)
                        break
                    except FileNotFoundError:
                        if self.data_shm is not None:
                            self.data_shm.close()
                            self.data_shm = None
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f"Shared memory initialization timed out for {self.symbol} {self.timeframe}")
                        time.sleep(0.01)
        else:
            try:
                self.data_shm = shared_memory.SharedMemory(name=self.data_name)
                self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)
            except FileNotFoundError:
                logger.error(f"Shared memory blocks not found for {self.symbol} {self.timeframe}")
                raise
            except Exception as e:
                logger.error(f"Failed to attach to shared memory for {self.symbol} {self.timeframe}: {e}")
                raise

        # The creator may use a session-specific capacity. Derive it from the
        # attached block so workers use the same circular buffer.
        self.max_size = self.data_shm.size // (6 * 8)
        self.shape = (self.max_size, 6)
            
        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self.data_shm.buf)
        self.meta_array = np.ndarray((3,), dtype=np.int64, buffer=self.meta_shm.buf)
        
        if initialized_here:
            # Attaching processes must never erase data owned by the feed.
            self.array.fill(0.0)
            self.meta_array.fill(0)

    @property
    def current_index(self) -> int:
        return int(self.meta_array[0])
        
    @property
    def tick_counter(self) -> int:
        return int(self.meta_array[1])

    def is_tick_fresh(self, max_age_seconds: float = 15.0) -> bool:
        last_tick_ms = int(self.meta_array[2])
        return last_tick_ms > 0 and 0 <= time.time() - (last_tick_ms / 1000.0) <= max_age_seconds
        
    def advance_candle(self):
        """
        Moves the pointer forward when a candle closes.
        """
        idx = self.current_index
        next_idx = (idx + 1) % self.max_size
        self.meta_array[0] = next_idx
        # Reset the new slot
        self.array[next_idx].fill(0.0)
        
    def update_current_candle(self, price: float, volume: float, timestamp: float = None):
        """
        Updates the current forming candle with new tick data.
        """
        idx = self.current_index
        tick_timestamp = float(timestamp if timestamp is not None else time.time())
        candle_timestamp = int(tick_timestamp // 60) * 60

        active_timestamp = int(self.array[idx, 5]) if self.array[idx, 5] else 0
        if active_timestamp and candle_timestamp < active_timestamp:
            # Out-of-order broker ticks must not move the active candle backward.
            return

        if self.array[idx, 5] and self.array[idx, 5] != candle_timestamp:
            self.advance_candle()
            idx = self.current_index
        
        # If open is 0, initialize the candle
        if self.array[idx, 0] == 0.0:
            self.array[idx, 0] = price
            self.array[idx, 1] = price
            self.array[idx, 2] = price
            self.array[idx, 3] = price
            self.array[idx, 4] = volume
            self.array[idx, 5] = candle_timestamp
        else:
            # Update High
            if price > self.array[idx, 1]:
                self.array[idx, 1] = price
            # Update Low
            if price < self.array[idx, 2]:
                self.array[idx, 2] = price
            # Update Close
            self.array[idx, 3] = price
            # Accumulate Volume
            self.array[idx, 4] += volume
            self.array[idx, 5] = candle_timestamp
            
        self.meta_array[1] += 1
        self.meta_array[2] = int(time.time() * 1000)
            
    def get_latest_data(self, lookback: int = None):
        """
        Retrieves the data correctly ordered, unwrapping the circular buffer.
        """
        if lookback is None or lookback > self.max_size:
            lookback = self.max_size
        lookback = max(0, int(lookback))
        if lookback == 0:
            return np.empty((0, self.array.shape[1]), dtype=self.dtype)

        idx = self.current_index
        start = (idx - lookback + 1) % self.max_size

        # Copy only the requested chronological window. np.roll copied the full
        # shared-memory capacity on every slow-path evaluation, even when the
        # strategy only needed a small indicator warmup window.
        if start <= idx:
            return self.array[start:idx + 1].copy()
        return np.concatenate((self.array[start:], self.array[:idx + 1]), axis=0)

    def get_latest_price(self):
        """Return the latest forming candle close, or None if empty."""
        latest = self.array[self.current_index]
        if latest[0] == 0.0:
            return None
        # Basic data validation
        if not self._validate_price_data(latest):
            logger.warning(f"Invalid price data detected for {self.symbol}, returning None")
            return None
        return float(latest[3])
    
    def _validate_price_data(self, data_row):
        """Validate price data for integrity."""
        try:
            open_price = float(data_row[0])
            high_price = float(data_row[1])
            low_price = float(data_row[2])
            close_price = float(data_row[3])
            volume = float(data_row[4])
            
            # Basic validation
            if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                return False
            if high_price < low_price:
                return False
            if close_price > high_price or close_price < low_price:
                return False
            if volume < 0:
                return False
            
            return True
        except (ValueError, TypeError, IndexError):
            return False

    def close(self):
        """
        Must be called to unlink shared memory.
        """
        if self.data_shm:
            self.data_shm.close()
        if self.meta_shm:
            self.meta_shm.close()
            
    def unlink(self):
        """
        Only call this from the creator process to completely destroy the memory.
        """
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
                
    def preload_historical_data(self, max_lookback: int, validate: bool = True):
        """
        Preloads the exact historical depth required by execution.
        """
        from marketdata.services import MarketDataService
        
        try:
            if max_lookback > self.max_size:
                raise RuntimeError(f"SHM capacity {self.max_size} is below required depth {max_lookback}")

            if validate:
                readiness = MarketDataService.ensure_historical_candles(self.symbol, timeframe=self.timeframe, required_count=max_lookback)
                if not readiness["ready"]:
                    raise RuntimeError(
                        f"Historical data is incomplete for {self.symbol} {self.timeframe}: "
                        f"requested={readiness['requested']} available={readiness['available']} "
                        f"missing={readiness.get('missing', 0)} "
                        f"latest_expected={readiness.get('latest_expected')} "
                        f"latest_available={readiness.get('latest_available')}"
                    )

            candles = MarketDataService.list_candles(symbol=self.symbol, timeframe=self.timeframe, limit=max_lookback)

            if len(candles) < max_lookback:
                raise RuntimeError(f"Historical query returned only {len(candles)} candles for {self.symbol} {self.timeframe}; requested {max_lookback}")

            logger.info("Preloading %s historical candles for %s %s.", len(candles), self.symbol, self.timeframe)
            
            # Reset array before preloading
            self.array.fill(0.0)
            self.meta_array[0] = 0
            self.meta_array[1] = 0
            
            for i, candle in enumerate(candles):
                idx = self.current_index
                
                # Support both dict and Django model instance
                is_dict = isinstance(candle, dict)
                c_open = candle.get('open', 0.0) if is_dict else getattr(candle, 'open', 0.0)
                c_high = candle.get('high', 0.0) if is_dict else getattr(candle, 'high', 0.0)
                c_low = candle.get('low', 0.0) if is_dict else getattr(candle, 'low', 0.0)
                c_close = candle.get('close', 0.0) if is_dict else getattr(candle, 'close', 0.0)
                c_volume = candle.get('volume', 0.0) if is_dict else getattr(candle, 'volume', 0.0)
                
                self.array[idx, 0] = float(c_open)
                self.array[idx, 1] = float(c_high)
                self.array[idx, 2] = float(c_low)
                self.array[idx, 3] = float(c_close)
                self.array[idx, 4] = float(c_volume)
                candle_time = candle.get('time', 0.0) if is_dict else getattr(candle, 'time', 0.0)
                if hasattr(candle_time, 'timestamp'):
                    candle_time = candle_time.timestamp()
                self.array[idx, 5] = float(candle_time or 0.0)
                
                # Advance to next slot for the next candle
                if i < len(candles) - 1:
                    self.advance_candle()
                    
            logger.info(f"Successfully preloaded {len(candles)} candles for {self.symbol} {self.timeframe}.")
        except Exception as e:
            logger.exception(f"Failed to preload historical data for {self.symbol}: {e}")
            raise
