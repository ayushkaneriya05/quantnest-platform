"""
CacheView - Read-only interface for QuantNest Unified Cache
Prevents accidental mutation by strategy code.
Thread-safe reads with session-level locking.
"""

import logging
from typing import Dict, List, Any, Optional

from .unified_cache import unified_cache

logger = logging.getLogger(__name__)


class CacheView:
    """
    Read-only facade over QuantNestUnifiedCache.
    Prevents accidental mutation by strategy code.
    Thread-safe reads with session-level locking.
    """
    
    def __init__(self):
        """Initialize CacheView with reference to unified cache."""
        self._cache = unified_cache
    
    def get_orders(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get orders for a session (O(1) lookup).

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier

        Returns:
            List of order dictionaries
        """
        return self._cache.get_orders(scope, session_id)

    def get_positions(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get positions for a session (O(1) lookup).

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier

        Returns:
            List of position dictionaries
        """
        return self._cache.get_positions(scope, session_id)

    def get_funds(self, credential_id: int) -> Optional[Dict[str, Any]]:
        """
        Get funds for a credential (O(1) lookup).

        Args:
            credential_id: Broker credential ID

        Returns:
            Funds dictionary or None
        """
        return self._cache.get_funds(credential_id)

    def get_account_funds(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get funds for a paper account (O(1) lookup).

        Args:
            account_id: Paper account ID

        Returns:
            Funds dictionary or None
        """
        return self._cache.get_account_funds(account_id)

    def get_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> Dict[str, Any]:
        """
        Get runtime state for a session/instrument (O(1) lookup).

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            instrument_id: Instrument ID

        Returns:
            Runtime state dictionary
        """
        return self._cache.get_runtime_state(scope, session_id, instrument_id)
    
    def get_risk_metrics(self, scope: str, session_id: str) -> Dict[str, Any]:
        """
        Get risk metrics for a session (O(1) lookup).
        
        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            
        Returns:
            Risk metrics dictionary
        """
        return self._cache.get_risk_metrics(scope, session_id)
    
    def get_market_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get market quote for a symbol (delegates to existing QuoteStore).
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Quote dictionary or None
        """
        # Delegate to existing QuoteStore for FIELD namespace
        from marketdata.quote_store import QuoteStore
        return QuoteStore.get_latest(symbol)
    
    def get_session_version(self, session_id: str) -> int:
        """
        Get current version for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Version number
        """
        return self._cache.get_session_version(session_id)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Cache statistics dictionary
        """
        return self._cache.get_cache_stats()


# Global instance
cache_view = CacheView()