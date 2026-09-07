"""
Paper trading WebSocket simulator.
Simulates WebSocket behavior for paper trading using Django signals.
"""

import logging
from typing import Dict, Any
from django.utils import timezone
from django.db.models.signals import post_save, post_delete

from .base_websocket import BaseBrokerWebSocket

logger = logging.getLogger(__name__)


class PaperWebSocketSimulator(BaseBrokerWebSocket):
    """
    Simulated WebSocket for paper trading using DB triggers.
    
    Since paper trading doesn't have a real broker WebSocket, this class
    simulates WebSocket behavior by listening to Django model signals
    and triggering callbacks as if they were WebSocket updates.
    """
    
    def __init__(self, account):
        """
        Initialize paper WebSocket simulator.
        
        Args:
            account: PaperAccount instance to monitor
        """
        super().__init__()
        self.account = account
        self.signal_handlers = []
        self.is_connected = False
        self.is_subscribed = False
        
    def connect(self) -> None:
        """
        Connect to DB change notifications (simulated WebSocket).
        
        Registers Django signal handlers for PaperOrder, PaperPosition, and PaperTrade
        models to simulate real-time WebSocket updates.
        """
        try:
            from paper_trading.models import PaperOrder, PaperPosition, PaperTrade
            
            # Register signal handlers
            order_handler = self._create_order_handler(PaperOrder)
            position_handler = self._create_position_handler(PaperPosition)
            trade_handler = self._create_trade_handler(PaperTrade)
            
            post_save.connect(order_handler, sender=PaperOrder, weak=False)
            post_save.connect(position_handler, sender=PaperPosition, weak=False)
            post_save.connect(trade_handler, sender=PaperTrade, weak=False)
            
            self.signal_handlers = [order_handler, position_handler, trade_handler]
            self.is_connected = True
            logger.info(f"Connected to paper WebSocket simulator for account {self.account.id}")
            
        except Exception as e:
            logger.exception(f"Failed to connect to paper WebSocket simulator: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from paper WebSocket simulator."""
        try:
            from paper_trading.models import PaperOrder, PaperPosition, PaperTrade
            
            # Disconnect signal handlers
            for handler in self.signal_handlers:
                post_save.disconnect(handler)
            
            self.signal_handlers = []
            self.is_connected = False
            self.is_subscribed = False
            logger.info(f"Disconnected from paper WebSocket simulator for account {self.account.id}")
            
        except Exception as e:
            logger.exception(f"Error disconnecting from paper WebSocket simulator: {e}")
    
    def subscribe(self, data_types: list) -> None:
        """
        Subscribe to paper trading data types.
        
        For paper trading, all data types are always available via signals,
        so this is mainly for API compatibility.
        
        Args:
            data_types: List of data types to subscribe to
        """
        self.is_subscribed = True
        logger.info(f"Subscribed to paper data types: {data_types}")
    
    def _create_order_handler(self, model_class):
        """
        Create a signal handler for order updates.
        
        Args:
            model_class: PaperOrder model class
            
        Returns:
            Signal handler function
        """
        def handler(sender, instance, created, **kwargs):
            try:
                if instance.account_id == self.account.id:
                    normalized = self.normalize_order_update({
                        "orders": self._serialize_order(instance)
                    })
                    self._trigger_callbacks('orders', normalized)
                    logger.debug(f"Simulated paper order update: {instance.id}")
            except Exception as e:
                logger.exception(f"Error in paper order signal handler: {e}")
        
        return handler
    
    def _create_position_handler(self, model_class):
        """
        Create a signal handler for position updates.
        
        Args:
            model_class: PaperPosition model class
            
        Returns:
            Signal handler function
        """
        def handler(sender, instance, created, **kwargs):
            try:
                if instance.account_id == self.account.id:
                    normalized = self.normalize_position_update({
                        "positions": self._serialize_position(instance)
                    })
                    self._trigger_callbacks('positions', normalized)
                    logger.debug(f"Simulated paper position update: {instance.id}")
            except Exception as e:
                logger.exception(f"Error in paper position signal handler: {e}")
        
        return handler
    
    def _create_trade_handler(self, model_class):
        """
        Create a signal handler for trade updates.
        
        Args:
            model_class: PaperTrade model class
            
        Returns:
            Signal handler function
        """
        def handler(sender, instance, created, **kwargs):
            try:
                if instance.account_id == self.account.id:
                    normalized = self.normalize_trade_update({
                        "trades": self._serialize_trade(instance)
                    })
                    self._trigger_callbacks('trades', normalized)
                    logger.debug(f"Simulated paper trade update: {instance.id}")
            except Exception as e:
                logger.exception(f"Error in paper trade signal handler: {e}")
        
        return handler
    
    def _serialize_order(self, order) -> Dict[str, Any]:
        """Serialize PaperOrder to broker-like format."""
        return {
            "id": str(order.id),
            "exch_ord_id": f"PAPER-{order.id}",
            "symbol": order.instrument.sym_ticker if order.instrument else "",
            "qty": order.quantity,
            "filled_qty": order.filled_quantity,
            "remaining_quantity": order.quantity - order.filled_quantity,
            "status": self._map_paper_status(order.status),
            "traded_price": float(order.avg_fill_price or 0),
            "limit_price": float(order.price or 0),
            "stop_price": 0,
            "productType": order.product_type,
            "type": 2,  # MARKET
            "side": 1 if order.side == "BUY" else -1,
            "orderDateTime": order.executed_at.isoformat() if order.executed_at else order.placed_at.isoformat()
        }
    
    def _serialize_position(self, position) -> Dict[str, Any]:
        """Serialize PaperPosition to broker-like format."""
        return {
            "id": f"PAPER-POS-{position.id}",
            "symbol": position.instrument.sym_ticker if position.instrument else "",
            "net_qty": position.quantity,
            "qty": position.quantity,
            "net_avg": float(position.avg_price),
            "ltp": float(position.current_price),
            "unrealized_profit": float(position.unrealized_pnl),
            "realized_profit": float(position.realized_pnl or 0),
            "product_type": "",
            "side": 1 if position.side == "BUY" else -1,
            "exchange": "PAPER",
            "segment": "PAPER"
        }
    
    def _serialize_trade(self, trade) -> Dict[str, Any]:
        """Serialize PaperTrade to broker-like format."""
        return {
            "trade_number": f"PAPER-TRADE-{trade.id}",
            "order_number": str(trade.exit_order.id) if trade.exit_order else "",
            "symbol": trade.instrument.sym_ticker if trade.instrument else "",
            "qty": trade.quantity,
            "trade_price": float(trade.exit_price),
            "trade_value": float(trade.exit_price * trade.quantity),
            "productType": "",
            "exchange": "PAPER",
            "segment": "PAPER",
            "side": 1 if trade.side == "BUY" else -1
        }
    
    def _map_paper_status(self, status: str) -> int:
        """Map paper order status to broker status code."""
        status_map = {
            "PENDING": 6,
            "PLACED": 6,
            "PARTIAL_FILL": 4,
            "FILLED": 2,
            "REJECTED": 5,
            "CANCELLED": 1,
            "EXPIRED": 1
        }
        return status_map.get(status, 6)
    
    def normalize_order_update(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize paper order update to standard format."""
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
        """Normalize paper trade update to standard format."""
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
        """Normalize paper position update to standard format."""
        positions = raw_data.get("positions", {})
        
        return {
            "broker_position_id": positions.get("id") or "",
            "symbol": positions.get("symbol") or "",
            "side": self._normalize_side(positions.get("side")),
            "quantity": int(positions.get("net_qty") or 0),
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
