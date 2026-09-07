"""
Abstract base class for broker WebSocket implementations.
All broker-specific WebSocket implementations must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class BaseBrokerWebSocket(ABC):
    """
    Abstract base class for broker WebSocket implementations.
    
    Provides a unified interface for real-time order, trade, and position updates
    across different brokers (Fyers, Zerodha, Angel, etc.).
    """
    
    def __init__(self):
        self.callbacks = defaultdict(list)
        self.is_connected = False
        self.is_subscribed = False
        
    @abstractmethod
    def connect(self) -> None:
        """
        Connect to the broker's WebSocket endpoint.
        
        Must implement broker-specific connection logic including:
        - Authentication
        - WebSocket endpoint URL
        - Connection parameters
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the broker's WebSocket endpoint.
        
        Must implement graceful disconnection logic.
        """
        pass
    
    @abstractmethod
    def subscribe(self, data_types: list) -> None:
        """
        Subscribe to broker data types.
        
        Args:
            data_types: List of data types to subscribe to (e.g., ['orders', 'trades', 'positions'])
        """
        pass
    
    @abstractmethod
    def normalize_order_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize broker-specific order update to standard format.
        
        Args:
            raw_data: Raw broker-specific order update data
            
        Returns:
            Normalized order data with standard field names:
            - broker_order_id: str
            - exchange_order_id: str
            - symbol: str
            - side: str (BUY/SELL)
            - quantity: int
            - filled_quantity: int
            - pending_quantity: int
            - status: int (broker status code)
            - avg_fill_price: float
            - updated_at: str (ISO format timestamp)
            - raw: dict (original broker data)
        """
        pass
    
    @abstractmethod
    def normalize_trade_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize broker-specific trade update to standard format.
        
        Args:
            raw_data: Raw broker-specific trade update data
            
        Returns:
            Normalized trade data with standard field names:
            - trade_number: str
            - order_number: str
            - symbol: str
            - side: str (BUY/SELL)
            - quantity: int
            - trade_price: float
            - trade_value: float
            - product_type: str
            - updated_at: str (ISO format timestamp)
            - raw: dict (original broker data)
        """
        pass
    
    @abstractmethod
    def normalize_position_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize broker-specific position update to standard format.
        
        Args:
            raw_data: Raw broker-specific position update data
            
        Returns:
            Normalized position data with standard field names:
            - broker_position_id: str
            - symbol: str
            - side: str (BUY/SELL)
            - quantity: int
            - avg_price: float
            - current_price: float
            - unrealized_pnl: float
            - product_type: str
            - updated_at: str (ISO format timestamp)
            - raw: dict (original broker data)
        """
        pass
    
    def on_order_update(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for order updates.
        
        Args:
            callback: Function to call when order update is received
        """
        self.callbacks['orders'].append(callback)
    
    def on_trade_update(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for trade updates.
        
        Args:
            callback: Function to call when trade update is received
        """
        self.callbacks['trades'].append(callback)
    
    def on_position_update(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for position updates.
        
        Args:
            callback: Function to call when position update is received
        """
        self.callbacks['positions'].append(callback)
    
    def on_general_message(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for general messages (e.g., login, eDIS, price alerts).
        
        Args:
            callback: Function to call when general message is received
        """
        self.callbacks['general'].append(callback)
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger all registered callbacks for a given event type.
        
        Args:
            event_type: Type of event ('orders', 'trades', 'positions', 'general')
            data: Data to pass to callbacks
        """
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.exception(f"Error in {event_type} callback: {e}")
    
    def _normalize_side(self, side_value: Any) -> str:
        """
        Normalize side value to standard BUY/SELL format.
        
        Args:
            side_value: Broker-specific side value
            
        Returns:
            'BUY' or 'SELL'
        """
        if side_value in (1, '1', 'BUY', 'buy'):
            return 'BUY'
        elif side_value in (-1, '-1', 'SELL', 'sell'):
            return 'SELL'
        else:
            logger.warning(f"Unknown side value: {side_value}, defaulting to BUY")
            return 'BUY'
