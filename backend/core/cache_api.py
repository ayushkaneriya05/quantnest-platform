"""Write interface for shared execution state."""

import logging
import json
from typing import Dict, Any

from django.core.cache import cache
from .shared_state_store import shared_state_store

logger = logging.getLogger(__name__)


class CacheApi:
    """
    Write interface for system engines backed by shared Redis state.
    Session-based updates use centralized versions and distributed locks.
    """
    
    def __init__(self):
        """Initialize CacheApi with the shared state store."""
        self._cache = shared_state_store
    
    def update_order(self, scope: str, session_id: str, order: Dict[str, Any]) -> bool:
        """
        Update or add an order for a session.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            order: Order dictionary

        Returns:
            True if successful
        """
        try:
            self._cache.upsert_order(scope, session_id, order)
            return True

        except Exception as e:
            logger.exception(f"Error updating order for {scope}:{session_id}: {e}")
            return False

    def update_position(self, scope: str, session_id: str, position: Dict[str, Any]) -> bool:
        """
        Update or add a position for a session.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            position: Position dictionary

        Returns:
            True if successful
        """
        try:
            self._cache.upsert_position(scope, session_id, position)
            return True

        except Exception as e:
            logger.exception(f"Error updating position for {scope}:{session_id}: {e}")
            return False
    
    def update_funds(self, credential_id: int, funds: Dict[str, Any]) -> bool:
        """
        Update funds for a credential.
        
        Args:
            credential_id: Broker credential ID
            funds: Funds dictionary
            
        Returns:
            True if successful
        """
        try:
            self._cache.set_funds(credential_id, funds)
            return True
        except Exception as e:
            logger.exception(f"Error updating funds for credential {credential_id}: {e}")
            return False
    
    def update_runtime_state(self, scope: str, session_id: str, instrument_id: int, state: Dict[str, Any]) -> bool:
        """
        Update runtime state for a session/instrument.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            instrument_id: Instrument ID
            state: Runtime state dictionary

        Returns:
            True if successful
        """
        try:
            self._cache.update_runtime_state(scope, session_id, instrument_id, state)
            if "phase" in state:
                self._publish_runtime_lifecycle(scope, session_id, instrument_id, state)
            return True
        except Exception as e:
            logger.exception(f"Error updating runtime state for {scope}:{session_id}:{instrument_id}: {e}")
            return False

    @staticmethod
    def _publish_runtime_lifecycle(scope, session_id, instrument_id, updates):
        try:
            if hasattr(cache, "client"):
                redis_client = cache.client.get_client()
            else:
                import redis
                from django.conf import settings
                redis_client = redis.from_url(settings.REDIS_URL)
            redis_client.xadd(
                "runtime_state_lifecycle",
                {"payload": json.dumps({
                    "scope": scope,
                    "session_id": str(session_id),
                    "instrument_id": instrument_id,
                    "updates": updates,
                })},
                maxlen=10000,
                approximate=True,
            )
        except Exception:
            logger.warning("Runtime lifecycle stream append failed", exc_info=True)

    def update_risk_metrics(self, scope: str, session_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Update risk metrics for a session.
        
        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            metrics: Risk metrics dictionary
            
        Returns:
            True if successful
        """
        try:
            self._cache.update_risk_metrics(scope, session_id, metrics)
            return True
        except Exception as e:
            logger.exception(f"Error updating risk metrics for {scope}:{session_id}: {e}")
            return False
    
    def update_market_quote(self, symbol: str, quote: Dict[str, Any]) -> bool:
        """
        Update market quote (delegates to existing QuoteStore).
        
        Args:
            symbol: Instrument symbol
            quote: Quote dictionary
            
        Returns:
            True if successful
        """
        # Delegate to existing QuoteStore for FIELD namespace
        try:
            from marketdata.quote_store import QuoteStore
            QuoteStore.set_latest(symbol, quote)
            return True
        except Exception as e:
            logger.exception(f"Error updating market quote for {symbol}: {e}")
            return False
    
    def remove_order(self, scope: str, session_id: str, order_id: str) -> bool:
        """
        Remove an order from the session.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            order_id: Order ID or broker order ID

        Returns:
            True if successful
        """
        try:
            return self._cache.remove_order(scope, session_id, order_id)
        except Exception as e:
            logger.exception(f"Error removing order {order_id} from {scope}:{session_id}: {e}")
            return False

    def remove_position(self, scope: str, session_id: str, position_id: str) -> bool:
        """
        Remove a position from the session.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            position_id: Position ID

        Returns:
            True if successful
        """
        try:
            return self._cache.remove_position(scope, session_id, position_id)
        except Exception as e:
            logger.exception(f"Error removing position {position_id} from {scope}:{session_id}: {e}")
            return False

    def clear_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> bool:
        """
        Clear runtime state for a session/instrument.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            instrument_id: Instrument ID

        Returns:
            True if successful
        """
        try:
            self._cache.clear_runtime_state(scope, session_id, instrument_id)
            return True
        except Exception as e:
            logger.exception(f"Error clearing runtime state for {scope}:{session_id}:{instrument_id}: {e}")
            return False

    def clear_session(self, scope: str, session_id: str) -> bool:
        """
        Clear all data for a session.

        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier

        Returns:
            True if successful
        """
        try:
            self._cache.clear_session(scope, session_id)
            return True
        except Exception as e:
            logger.exception(f"Error clearing session {scope}:{session_id}: {e}")
            return False

    def update_session_funds(self, scope: str, session_id: str, funds: Dict[str, Any]) -> bool:
        try:
            self._cache.set_session_funds(scope, str(session_id), funds)
            return True
        except Exception as e:
            logger.exception("Error updating funds for %s session %s: %s", scope, session_id, e)
            return False

    # ==================== Instrument Cache ====================

    def get_instrument_cache(self) -> Dict[int, Dict[str, Any]]:
        """
        Get instrument cache for fast resolution.

        Returns:
            Dictionary mapping instrument IDs to instrument data
        """
        try:
            cache_key = "instruments:cache"
            return self._cache.get(cache_key) or {}
        except Exception as e:
            logger.exception(f"Error getting instrument cache: {e}")
            return {}

    def update_instrument_cache(self, instrument_id: int, instrument_data: Dict[str, Any]) -> bool:
        """
        Update instrument cache for fast resolution.

        Args:
            instrument_id: Instrument ID
            instrument_data: Instrument data dictionary

        Returns:
            True if successful
        """
        try:
            cache_key = "instruments:cache"
            cache = self.get_instrument_cache()
            cache[instrument_id] = instrument_data
            self._cache.set(cache_key, cache)
            return True
        except Exception as e:
            logger.exception(f"Error updating instrument cache for instrument {instrument_id}: {e}")
            return False


# Global instance
cache_api = CacheApi()