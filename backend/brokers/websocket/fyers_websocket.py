"""
Fyers broker WebSocket implementation for real-time order, trade, and position updates.
"""

import logging
from typing import Dict, Any
from django.utils import timezone
from django.conf import settings
from common.enums import Side

from .base_websocket import BaseBrokerWebSocket

logger = logging.getLogger(__name__)


class FyersOrderWebSocket(BaseBrokerWebSocket):
    """
    Fyers order WebSocket implementation using fyers-apiv3 SDK.
    
    Provides real-time updates for:
    - Orders (on_orders)
    - Trades (on_trades)
    - Positions (on_positions)
    - General messages (on_general)
    """
    
    # Fyers order status codes
    STATUS_CANCELLED = 1
    STATUS_FILLED = 2
    STATUS_TRANSIT = 4
    STATUS_REJECTED = 5
    STATUS_PENDING = 6
    
    def __init__(self, credential):
        """
        Initialize Fyers order WebSocket.
        
        Args:
            credential: BrokerCredential instance for Fyers
        """
        super().__init__()
        self.credential = credential
        self.socket = None
        self.access_token = None
        
    def _get_valid_token(self) -> str:
        """
        Get valid access token from broker session.
        
        Returns:
            Access token string in format "client_id:access_token"
            
        Raises:
            ValueError: If no valid session exists
        """
        from brokers.models import BrokerSession
        
        session = self.credential.sessions.filter(
            is_valid=True,
            token_expiry__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not session:
            raise ValueError(
                f"No valid Fyers session found for credential {self.credential.id}. "
                "Please authenticate the broker credential."
            )
        
        self.access_token = session.access_token
        return f"{self.credential.client_id}:{self.access_token}"
    
    def connect(self) -> None:
        """
        Connect to Fyers order WebSocket.
        
        Raises:
            RuntimeError: If fyers-apiv3 is not available
            ValueError: If authentication fails
        """
        try:
            from fyers_apiv3.FyersWebsocket import order_ws
        except ImportError:
            raise RuntimeError(
                "fyers-apiv3 package is not available. "
                "Install it with: pip install fyers-apiv3==3.1.16"
            )
        
        try:
            access_token = self._get_valid_token()
            
            self.socket = order_ws.FyersOrderSocket(
                access_token=access_token,
                log_path=str(settings.BASE_DIR / "logs") if hasattr(settings, 'BASE_DIR') else "",
                on_orders=self._on_order_message,
                on_trades=self._on_trade_message,
                on_positions=self._on_position_message,
                on_general=self._on_general_message,
            )
            
            self.socket.connect()
            self.is_connected = True
            logger.info(f"Connected to Fyers order WebSocket for credential {self.credential.id}")
            
        except Exception as e:
            logger.exception(f"Failed to connect to Fyers order WebSocket: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Fyers order WebSocket."""
        if self.socket:
            try:
                self.socket.close()
                self.is_connected = False
                self.is_subscribed = False
                logger.info(f"Disconnected from Fyers order WebSocket for credential {self.credential.id}")
            except Exception as e:
                logger.exception(f"Error disconnecting from Fyers order WebSocket: {e}")
    
    def subscribe(self, data_types: list) -> None:
        """
        Subscribe to Fyers data types.
        
        Args:
            data_types: List of data types to subscribe to.
                       Valid values: 'orders', 'trades', 'positions', 'general'
                       Use comma-separated string: "OnOrders,OnTrades,OnPositions"
        """
        if not self.is_connected:
            raise RuntimeError("WebSocket is not connected. Call connect() first.")
        
        try:
            # Map our data types to Fyers subscription format
            type_mapping = {
                'orders': 'OnOrders',
                'trades': 'OnTrades',
                'positions': 'OnPositions',
                'general': 'OnGeneral'
            }
            
            fyers_types = []
            for dt in data_types:
                fyers_type = type_mapping.get(dt.lower())
                if fyers_type:
                    fyers_types.append(fyers_type)
            
            if not fyers_types:
                logger.warning("No valid data types provided for subscription")
                return
            
            subscription_string = ",".join(fyers_types)
            self.socket.subscribe(data_type=subscription_string)
            self.is_subscribed = True
            logger.info(f"Subscribed to Fyers data types: {subscription_string}")
            
        except Exception as e:
            logger.exception(f"Failed to subscribe to Fyers data types: {e}")
            raise
    
    def _on_order_message(self, message: Dict[str, Any]) -> None:
        """
        Process Fyers order WebSocket message.
        
        Args:
            message: Raw WebSocket message from Fyers
        """
        try:
            if message.get("s") == "ok":
                normalized = self.normalize_order_update(message)
                self._trigger_callbacks('orders', normalized)
                logger.debug(f"Processed Fyers order update: {normalized.get('broker_order_id')}")
            else:
                logger.warning(f"Fyers order message error: {message}")
        except Exception as e:
            logger.exception(f"Error processing Fyers order message: {e}")
    
    def _on_trade_message(self, message: Dict[str, Any]) -> None:
        """
        Process Fyers trade WebSocket message.
        
        Args:
            message: Raw WebSocket message from Fyers
        """
        try:
            if message.get("s") == "ok":
                normalized = self.normalize_trade_update(message)
                self._trigger_callbacks('trades', normalized)
                logger.debug(f"Processed Fyers trade update: {normalized.get('trade_number')}")
            else:
                logger.warning(f"Fyers trade message error: {message}")
        except Exception as e:
            logger.exception(f"Error processing Fyers trade message: {e}")
    
    def _on_position_message(self, message: Dict[str, Any]) -> None:
        """
        Process Fyers position WebSocket message.
        
        Args:
            message: Raw WebSocket message from Fyers
        """
        try:
            if message.get("s") == "ok":
                normalized = self.normalize_position_update(message)
                self._trigger_callbacks('positions', normalized)
                logger.debug(f"Processed Fyers position update: {normalized.get('broker_position_id')}")
            else:
                logger.warning(f"Fyers position message error: {message}")
        except Exception as e:
            logger.exception(f"Error processing Fyers position message: {e}")
    
    def _on_general_message(self, message: Dict[str, Any]) -> None:
        """
        Process Fyers general WebSocket message (login, eDIS, price alerts).
        
        Args:
            message: Raw WebSocket message from Fyers
        """
        try:
            self._trigger_callbacks('general', message)
            logger.debug(f"Processed Fyers general message")
        except Exception as e:
            logger.exception(f"Error processing Fyers general message: {e}")
    
    def normalize_order_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Fyers order update to standard format.
        
        Args:
            raw_data: Raw Fyers order WebSocket message
            
        Returns:
            Normalized order data with standard field names
        """
        orders = raw_data.get("orders", {})
        
        return {
            "broker_order_id": orders.get("id") or "",
            "exchange_order_id": orders.get("exch_ord_id") or "",
            "symbol": orders.get("symbol") or "",
            "side": self._normalize_side(orders.get("side")),
            "quantity": int(orders.get("qty") or 0),
            "filled_quantity": int(orders.get("filled_qty") or 0),
            "pending_quantity": int(orders.get("remaining_quantity") or 0),
            "status": int(orders.get("status") or 0),
            "avg_fill_price": float(orders.get("traded_price") or 0),
            "limit_price": float(orders.get("limit_price") or 0),
            "stop_price": float(orders.get("stop_price") or 0),
            "product_type": orders.get("productType") or "",
            "order_type": orders.get("type"),
            "updated_at": timezone.now().isoformat(),
            "raw": orders
        }
    
    def normalize_trade_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Fyers trade update to standard format.
        
        Args:
            raw_data: Raw Fyers trade WebSocket message
            
        Returns:
            Normalized trade data with standard field names
        """
        trades = raw_data.get("trades", {})
        
        return {
            "trade_number": trades.get("trade_number") or "",
            "order_number": trades.get("order_number") or "",
            "symbol": trades.get("symbol") or "",
            "side": self._normalize_side(trades.get("side")),
            "quantity": int(trades.get("qty") or 0),
            "trade_price": float(trades.get("trade_price") or 0),
            "trade_value": float(trades.get("trade_value") or 0),
            "product_type": trades.get("productType") or "",
            "exchange": trades.get("exchange") or "",
            "segment": trades.get("segment") or "",
            "updated_at": timezone.now().isoformat(),
            "raw": trades
        }
    
    def normalize_position_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Fyers position update to standard format.
        
        Args:
            raw_data: Raw Fyers position WebSocket message
            
        Returns:
            Normalized position data with standard field names
        """
        positions = raw_data.get("positions", {})
        net_quantity = int(positions.get("net_qty") or 0)
        position_side = self._normalize_side(positions.get("side"))
        if net_quantity < 0:
            position_side = Side.SELL
        elif net_quantity > 0:
            position_side = Side.BUY
        
        return {
            "broker_position_id": positions.get("id") or "",
            "symbol": positions.get("symbol") or "",
            "side": position_side,
            "quantity": abs(net_quantity),
            "avg_price": float(positions.get("net_avg") or 0),
            "current_price": float(positions.get("ltp") or 0),
            "unrealized_pnl": float(positions.get("unrealized_profit") or 0),
            "realized_pnl": float(positions.get("realized_profit") or 0),
            "product_type": positions.get("product_type") or "",
            "exchange": positions.get("exchange") or "",
            "segment": positions.get("segment") or "",
            "updated_at": timezone.now().isoformat(),
            "raw": positions
        }
