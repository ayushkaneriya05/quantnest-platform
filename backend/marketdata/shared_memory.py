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
        self.data_name = f"data_v2_{safe_sym}_{timeframe}"
        self.meta_name = f"meta_v2_{safe_sym}_{timeframe}"
        
        self.data_shm = None
        self.meta_shm = None
        self.array = None
        self.meta_array = None
        
        self._init_memory(create)

    def _init_memory(self, create: bool):
        # Data block: max_size * 6 * 8 bytes (float64)
        data_bytes = self.max_size * 6 * 8
        # Meta block: 2 int64 (16 bytes) for [current_index, tick_counter]
        meta_bytes = 16
        
        if create:
            try:
                self.data_shm = shared_memory.SharedMemory(name=self.data_name, create=True, size=data_bytes)
                self.meta_shm = shared_memory.SharedMemory(name=self.meta_name, create=True, size=meta_bytes)
            except FileExistsError:
                # If they exist, attach to them
                self.data_shm = shared_memory.SharedMemory(name=self.data_name)
                self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)
        else:
            self.data_shm = shared_memory.SharedMemory(name=self.data_name)
            self.meta_shm = shared_memory.SharedMemory(name=self.meta_name)

        # The creator may use a session-specific capacity. Derive it from the
        # attached block so workers use the same circular buffer.
        self.max_size = self.data_shm.size // (6 * 8)
        self.shape = (self.max_size, 6)
            
        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self.data_shm.buf)
        self.meta_array = np.ndarray((2,), dtype=np.int64, buffer=self.meta_shm.buf)
        
        if create:
            # Initialize to zero
            self.array.fill(0.0)
            self.meta_array.fill(0)

    @property
    def current_index(self) -> int:
        return int(self.meta_array[0])
        
    @property
    def tick_counter(self) -> int:
        return int(self.meta_array[1])
        
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
            
    def get_latest_data(self, lookback: int = None):
        """
        Retrieves the data correctly ordered, unwrapping the circular buffer.
        """
        if lookback is None or lookback > self.max_size:
            lookback = self.max_size
            
        idx = self.current_index
        
        # Roll the array so the oldest data is at 0 and newest is at the end
        # 'idx' is the active unclosed candle, so it should be the very last element.
        # We roll by -(idx + 1) to put (idx + 1) at the start and idx at the end.
        rolled = np.roll(self.array, -(idx + 1), axis=0)
        
        return rolled[-lookback:]

    def get_latest_price(self):
        """Return the latest forming candle close, or None if empty."""
        latest = self.array[self.current_index]
        if latest[0] == 0.0:
            return None
        return float(latest[3])

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
                
    def preload_historical_data(self, max_lookback: int):
        """
        Preloads historical data from the database into the shared memory buffer.
        """
        from marketdata.services import MarketDataService
        
        try:
            candles = MarketDataService.list_candles(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=max_lookback
            )
            if not candles:
                logger.info(f"No historical candles found for {self.symbol} {self.timeframe} to preload.")
                return
                
            logger.info(f"Preloading {len(candles)} historical candles for {self.symbol} {self.timeframe} into SHM.")
            
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
