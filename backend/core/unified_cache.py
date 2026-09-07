"""
QuantNest Unified Cache (QUC)
Central in-memory database for portfolio state (STATE namespace).
O(1) lookups with indexed structures for high throughput.
"""

import threading
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class QuantNestUnifiedCache:
    """
    Central in-memory database for portfolio state (STATE namespace).
    O(1) lookups with indexed structures for high throughput.
    
    Features:
    - Session-based partitioning for high concurrency
    - Session-level locks instead of global locks
    - Version vectors per session for conflict detection
    - Background async Redis persistence (non-blocking)
    - O(1) lookups via indexed dictionaries
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(QuantNestUnifiedCache, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the unified cache data structures."""
        # Indexed data structures (scope:session-based partitioning to prevent collisions)
        self._orders_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # key: "{scope}:{session_id}"
        self._positions_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # key: "{scope}:{session_id}"
        self._funds_by_credential: Dict[int, Dict[str, Any]] = {}  # key: credential_id (live only)
        self._funds_by_account: Dict[int, Dict[str, Any]] = {}  # key: account_id (paper only)
        self._runtime_state: Dict[str, Dict[str, Any]] = {}  # key: "{scope}:{session_id}:{instrument_id}"
        self._risk_metrics: Dict[str, Dict[str, Any]] = {}  # key: "{scope}:{session_id}"
        
        # Session-based locking for high throughput
        self._session_locks: Dict[str, threading.RLock] = defaultdict(threading.RLock)
        
        # Version control per session
        self._session_versions: Dict[str, int] = defaultdict(int)
        
        # Global event sequence
        self._event_sequence: int = 0
        self._sequence_lock = threading.Lock()
        
        logger.info("QuantNest Unified Cache initialized")

    def get_session_lock(self, session_id: str) -> threading.RLock:
        """Get session-specific lock for thread-safe operations."""
        return self._session_locks[session_id]
    
    def get_next_version(self, session_id: str) -> int:
        """Get next version number for a session."""
        with self._sequence_lock:
            self._session_versions[session_id] += 1
            return self._session_versions[session_id]
    
    def get_next_sequence(self) -> int:
        """Get next global event sequence number."""
        with self._sequence_lock:
            self._event_sequence += 1
            return self._event_sequence
    
    # ==================== Orders ====================

    def get_orders(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        """Get orders for a session (O(1) lookup)."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            return self._orders_by_session.get(key, []).copy()

    def add_order(self, scope: str, session_id: str, order: Dict[str, Any]) -> None:
        """Add an order to the session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            order['_version'] = self.get_next_version(key)
            order['_sequence'] = self.get_next_sequence()
            order['_updated_at'] = datetime.now().isoformat()
            self._orders_by_session[key].append(order)
            logger.debug(f"Added order for {key}, version {order['_version']}")

    def update_order(self, scope: str, session_id: str, order_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing order."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            for order in self._orders_by_session[key]:
                if order.get('id') == order_id or order.get('broker_order_id') == order_id:
                    order.update(updates)
                    order['_version'] = self.get_next_version(key)
                    order['_sequence'] = self.get_next_sequence()
                    order['_updated_at'] = datetime.now().isoformat()
                    logger.debug(f"Updated order {order_id} for {key}, version {order['_version']}")
                    return True
            return False

    def remove_order(self, scope: str, session_id: str, order_id: str) -> bool:
        """Remove an order from the session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            orders = self._orders_by_session[key]
            for i, order in enumerate(orders):
                if order.get('id') == order_id or order.get('broker_order_id') == order_id:
                    orders.pop(i)
                    logger.debug(f"Removed order {order_id} from {key}")
                    return True
            return False
    
    # ==================== Positions ====================

    def get_positions(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        """Get positions for a session (O(1) lookup)."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            return self._positions_by_session.get(key, []).copy()

    def add_position(self, scope: str, session_id: str, position: Dict[str, Any]) -> None:
        """Add a position to the session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            position['_version'] = self.get_next_version(key)
            position['_sequence'] = self.get_next_sequence()
            position['_updated_at'] = datetime.now().isoformat()
            self._positions_by_session[key].append(position)
            logger.debug(f"Added position for {key}, version {position['_version']}")

    def update_position(self, scope: str, session_id: str, position_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing position."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            for position in self._positions_by_session[key]:
                if position.get('id') == position_id:
                    position.update(updates)
                    position['_version'] = self.get_next_version(key)
                    position['_sequence'] = self.get_next_sequence()
                    position['_updated_at'] = datetime.now().isoformat()
                    logger.debug(f"Updated position {position_id} for {key}, version {position['_version']}")
                    return True
            return False

    def remove_position(self, scope: str, session_id: str, position_id: str) -> bool:
        """Remove a position from the session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            positions = self._positions_by_session[key]
            for i, position in enumerate(positions):
                if position.get('id') == position_id:
                    positions.pop(i)
                    logger.debug(f"Removed position {position_id} from {key}")
                    return True
            return False
    
    # ==================== Funds ====================
    
    def get_funds(self, credential_id: int) -> Optional[Dict[str, Any]]:
        """Get funds for a credential (O(1) lookup)."""
        # Funds don't need session locking
        return self._funds_by_credential.get(credential_id, {}).copy()
    
    def set_funds(self, credential_id: int, funds: Dict[str, Any]) -> None:
        """Set funds for a credential."""
        funds['_version'] = self.get_next_version(f"credential_{credential_id}")
        funds['_sequence'] = self.get_next_sequence()
        funds['_updated_at'] = datetime.now().isoformat()
        self._funds_by_credential[credential_id] = funds
        logger.debug(f"Updated funds for credential {credential_id}, version {funds['_version']}")

    # ==================== Account Funds (Paper Trading) ====================

    def get_account_funds(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get funds for a paper account (O(1) lookup)."""
        return self._funds_by_account.get(account_id, {}).copy()

    def set_account_funds(self, account_id: int, funds: Dict[str, Any]) -> None:
        """Set funds for a paper account."""
        funds['_version'] = self.get_next_version(f"account_{account_id}")
        funds['_sequence'] = self.get_next_sequence()
        funds['_updated_at'] = datetime.now().isoformat()
        self._funds_by_account[account_id] = funds
        logger.debug(f"Updated account funds for account {account_id}, version {funds['_version']}")
    
    # ==================== Runtime State ====================

    def get_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> Dict[str, Any]:
        """Get runtime state for a session/instrument (O(1) lookup)."""
        key = f"{scope}:{session_id}:{instrument_id}"
        with self.get_session_lock(key):
            return self._runtime_state.get(key, {}).copy()

    def set_runtime_state(self, scope: str, session_id: str, instrument_id: int, state: Dict[str, Any]) -> None:
        """Set runtime state for a session/instrument."""
        key = f"{scope}:{session_id}:{instrument_id}"
        with self.get_session_lock(key):
            state['_version'] = self.get_next_version(key)
            state['_sequence'] = self.get_next_sequence()
            state['_updated_at'] = datetime.now().isoformat()
            self._runtime_state[key] = state
            logger.debug(f"Updated runtime state for {key}, version {state['_version']}")

    def update_runtime_state(self, scope: str, session_id: str, instrument_id: int, updates: Dict[str, Any]) -> None:
        """Update runtime state for a session/instrument."""
        key = f"{scope}:{session_id}:{instrument_id}"
        with self.get_session_lock(key):
            if key not in self._runtime_state:
                self._runtime_state[key] = {}
            self._runtime_state[key].update(updates)
            self._runtime_state[key]['_version'] = self.get_next_version(key)
            self._runtime_state[key]['_sequence'] = self.get_next_sequence()
            self._runtime_state[key]['_updated_at'] = datetime.now().isoformat()
            logger.debug(f"Updated runtime state for {key}, version {self._runtime_state[key]['_version']}")

    def clear_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> None:
        """Clear runtime state for a session/instrument."""
        key = f"{scope}:{session_id}:{instrument_id}"
        with self.get_session_lock(key):
            if key in self._runtime_state:
                del self._runtime_state[key]
                logger.debug(f"Cleared runtime state for {key}")
    
    # ==================== Risk Metrics ====================
    
    def get_risk_metrics(self, scope: str, session_id: str) -> Dict[str, Any]:
        """Get risk metrics for a session (O(1) lookup)."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(session_id):
            return self._risk_metrics.get(key, {}).copy()
    
    def set_risk_metrics(self, scope: str, session_id: str, metrics: Dict[str, Any]) -> None:
        """Set risk metrics for a session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(session_id):
            metrics['_version'] = self.get_next_version(session_id)
            metrics['_sequence'] = self.get_next_sequence()
            metrics['_updated_at'] = datetime.now().isoformat()
            self._risk_metrics[key] = metrics
            logger.debug(f"Updated risk metrics for {key}, version {metrics['_version']}")
    
    def update_risk_metrics(self, scope: str, session_id: str, updates: Dict[str, Any]) -> None:
        """Update risk metrics for a session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(session_id):
            if key not in self._risk_metrics:
                self._risk_metrics[key] = {}
            self._risk_metrics[key].update(updates)
            self._risk_metrics[key]['_version'] = self.get_next_version(session_id)
            self._risk_metrics[key]['_sequence'] = self.get_next_sequence()
            self._risk_metrics[key]['_updated_at'] = datetime.now().isoformat()
            logger.debug(f"Updated risk metrics for {key}, version {self._risk_metrics[key]['_version']}")
    
    # ==================== Session Management ====================

    def clear_session(self, scope: str, session_id: str) -> None:
        """Clear all data for a session."""
        key = f"{scope}:{session_id}"
        with self.get_session_lock(key):
            self._orders_by_session[key] = []
            self._positions_by_session[key] = []
            # Clear runtime states for this session
            keys_to_remove = [k for k in self._runtime_state.keys() if k.startswith(f"{scope}:{session_id}:")]
            for state_key in keys_to_remove:
                del self._runtime_state[state_key]
            # Clear risk metrics for this session
            risk_key = f"{scope}:{session_id}"
            if risk_key in self._risk_metrics:
                del self._risk_metrics[risk_key]
            logger.info(f"Cleared all data for {key}")
    
    def get_session_version(self, session_id: str) -> int:
        """Get current version for a session."""
        return self._session_versions.get(session_id, 0)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "total_sessions": len(self._orders_by_session),
            "total_orders": sum(len(orders) for orders in self._orders_by_session.values()),
            "total_positions": sum(len(positions) for positions in self._positions_by_session.values()),
            "total_runtime_states": len(self._runtime_state),
            "total_risk_metrics": len(self._risk_metrics),
            "total_credentials": len(self._funds_by_credential),
            "total_accounts": len(self._funds_by_account),
            "event_sequence": self._event_sequence,
        }


# Global instance
unified_cache = QuantNestUnifiedCache()