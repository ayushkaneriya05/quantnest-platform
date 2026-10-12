"""
Live WebSocket State Processor
Processes WebSocket updates and maintains state consistency for live trading.
Shares account ownership and cumulative fill accounting with REST reconciliation.
"""

import logging
import threading
from brokers.websocket.factory import BrokerWebSocketFactory

logger = logging.getLogger(__name__)


class LiveWebSocketProcessor:
    """
    Processes WebSocket updates and maintains state consistency.
    Broker-confirmed observations from WebSocket and REST share one fill writer.
    """
    
    def __init__(self, credential):
        """
        Initialize live WebSocket processor.
        
        Args:
            credential: BrokerCredential instance
        """
        self.credential = credential
        self.websocket = None
        self.sync_lock = threading.Lock()
        self.is_running = False
        self.auth_session_id = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    @property
    def is_healthy(self):
        return bool(self.is_running and self.websocket and self.websocket.is_connected and self.websocket.is_subscribed)
        
    def start(self) -> None:
        """
        Start WebSocket processing.
        
        Creates WebSocket connection, registers callbacks, and starts listening.
        """
        try:
            # Create WebSocket instance
            self.websocket = BrokerWebSocketFactory.create(self.credential)
            
            # Register state update callbacks
            self.websocket.on_order_update(self._handle_order_update)
            self.websocket.on_trade_update(self._handle_trade_update)
            self.websocket.on_position_update(self._handle_position_update)
            self.websocket.on_general_message(self._handle_general_message)
            
            # Connect and subscribe
            self.websocket.connect()
            self.websocket.subscribe(['orders', 'trades', 'positions'])
            self.auth_session_id = getattr(self.websocket, "auth_session_id", None)
            
            self.is_running = True
            self.reconnect_attempts = 0
            logger.info(f"Live WebSocket processor started for credential {self.credential.id}")
            
        except Exception as e:
            logger.exception(f"Failed to start live WebSocket processor: {e}")
            raise
    
    def stop(self) -> None:
        """Stop WebSocket processing."""
        try:
            if self.websocket:
                self.websocket.disconnect()
            self.is_running = False
            logger.info(f"Live WebSocket processor stopped for credential {self.credential.id}")
        except Exception as e:
            logger.exception(f"Error stopping live WebSocket processor: {e}")
    

    def _handle_order_update(self, order_data):
        from live_trading.order_processor import apply_order_observation
        from django.db import close_old_connections
        with self.sync_lock:
            close_old_connections()
            try:
                apply_order_observation(self.credential, order_data)
            except Exception:
                logger.exception("Broker order update failed credential=%s", self.credential.pk)
            finally:
                close_old_connections()

    def _handle_trade_update(self, trade_data):
        # A trade notification wakes reconciliation; it is not a second fill writer.
        from live_trading.tasks import reconcile_all_active_accounts
        from core.redis import runtime_redis
        if runtime_redis().set(f"quantnest:broker-reconcile:{self.credential.pk}", "1", nx=True, ex=2):
            reconcile_all_active_accounts.delay(self.credential.pk)

    def _handle_position_update(self, position_data):
        from live_trading.order_processor import observe_account_position
        from django.db import close_old_connections
        with self.sync_lock:
            close_old_connections()
            try:
                observe_account_position(self.credential, position_data)
            except Exception:
                logger.exception("Broker position update failed credential=%s", self.credential.pk)
            finally:
                close_old_connections()

    def _handle_general_message(self, message):
        logger.debug("Broker control message credential=%s type=%s",
                     self.credential.pk, message.get("type") if isinstance(message, dict) else type(message).__name__)
