"""
Unified State Manager
Provides unified state management for both LIVE (WebSocket) and PAPER (DB) modes.
Single interface for strategy engine, abstracting data source differences.
"""

import logging
from typing import Dict, Any, Optional, List
from django.core.cache import cache
from django.utils import timezone

from .cache_view import cache_view
from .cache_api import cache_api

logger = logging.getLogger(__name__)


class UnifiedStateManager:
    """
    Unified state manager supporting both LIVE (WebSocket) and PAPER (DB) modes.
    
    This class provides a single interface for strategy engine to access:
    - Orders
    - Positions
    - Trades
    - Funds
    
    The actual data source (WebSocket vs DB) is abstracted based on the scope.
    """
    
    def __init__(self, scope: str):
        """
        Initialize unified state manager.
        
        Args:
            scope: Either "live" or "paper"
        """
        self.scope = scope
        self.mode = "websocket" if scope == "live" else "database"
        
    def get_orders(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Unified order retrieval using unified cache.

        Args:
            session_id: Session identifier

        Returns:
            List of order dictionaries
        """
        return cache_view.get_orders(self.scope, session_id)

    def get_positions(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Unified position retrieval using unified cache.

        Args:
            session_id: Session identifier

        Returns:
            List of position dictionaries
        """
        return cache_view.get_positions(self.scope, session_id)
    
    def get_trades(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Unified trade retrieval (delegates to database for now).
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of trade dictionaries
        """
        # For now, trades are still retrieved from database
        # They can be added to unified cache in the future
        if self.mode == "websocket":
            return self._get_trades_from_db(session_id)
        else:
            return self._get_trades_from_db(session_id)
    
    def get_funds(self, credential_id: int) -> Optional[Dict[str, Any]]:
        """
        Unified funds retrieval using unified cache.
        
        Args:
            credential_id: Broker credential ID
            
        Returns:
            Funds dictionary or None
        """
        return cache_view.get_funds(credential_id)
    
    def update_order(self, order_data: Dict[str, Any]) -> None:
        """
        Update order in unified cache.

        Args:
            order_data: Order data to update
        """
        session_id = order_data.get("session_id")
        if session_id:
            cache_api.update_order(self.scope, str(session_id), order_data)

    def update_position(self, position_data: Dict[str, Any]) -> None:
        """
        Update position in unified cache.

        Args:
            position_data: Position data to update
        """
        session_id = position_data.get("session_id")
        if session_id:
            cache_api.update_position(self.scope, str(session_id), position_data)
    
    def _get_trades_from_db(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get trades from database (paper trading).
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of trade dictionaries from DB
        """
        if self.scope == "paper":
            from paper_trading.models import PaperTrade, PaperTradingSession
            
            try:
                session = PaperTradingSession.objects.get(id=session_id)
                trades = PaperTrade.objects.filter(account=session.account).order_by('-exit_time')
                
                return [
                    {
                        "id": str(trade.id),
                        "trade_number": f"PAPER-TRADE-{trade.id}",
                        "order_number": str(trade.exit_order.id) if trade.exit_order else "",
                        "symbol": trade.instrument.sym_ticker if trade.instrument else "",
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "trade_price": float(trade.exit_price),
                        "trade_value": float(trade.exit_price * trade.quantity),
                        "product_type": "",
                        "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
                    }
                    for trade in trades
                ]
            except PaperTradingSession.DoesNotExist:
                logger.warning(f"Paper trading session {session_id} not found")
                return []
            except Exception as e:
                logger.exception(f"Error getting paper trades for session {session_id}: {e}")
                return []
        else:
            # Live trades
            from live_trading.models import LiveTrade, TradingSession
            
            try:
                session = TradingSession.objects.get(id=session_id)
                trades = LiveTrade.objects.filter(allocation=session.allocation).order_by('-exit_time')
                
                return [
                    {
                        "id": str(trade.id),
                        "trade_number": f"LIVE-TRADE-{trade.id}",
                        "order_number": str(trade.order.id) if trade.order else "",
                        "symbol": trade.instrument.sym_ticker if trade.instrument else "",
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "trade_price": float(trade.exit_price),
                        "trade_value": float(trade.exit_price * trade.quantity),
                        "product_type": "",
                        "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
                    }
                    for trade in trades
                ]
            except TradingSession.DoesNotExist:
                logger.warning(f"Live trading session {session_id} not found")
                return []
            except Exception as e:
                logger.exception(f"Error getting live trades for session {session_id}: {e}")
                return []