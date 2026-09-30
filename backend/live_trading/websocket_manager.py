"""
WebSocket Connection Manager
Manages WebSocket connections for live trading with health monitoring and auto-reconnection.
"""

import logging
import threading
import time
from typing import Dict, Any
from django.utils import timezone
from live_trading.websocket_processor import LiveWebSocketProcessor

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections for live trading.
    
    Features:
    - Health monitoring for all active connections
    - Auto-reconnection on connection failure
    - Fallback to reconciliation if WebSocket fails
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize WebSocket connection manager."""
        self.active_processors: Dict[int, LiveWebSocketProcessor] = {}
        self.connection_health: Dict[int, Dict[str, Any]] = {}
        self.running = False
        self.health_check_interval = 30  # seconds
        self.health_check_thread = None
        self.lock = threading.RLock()

    def _publish_health(self, credential_id: int) -> None:
        """Publish process-local connection state for API/UI processes."""
        from django.core.cache import cache

        health = dict(self.connection_health.get(credential_id, {}))
        for key, value in list(health.items()):
            if hasattr(value, "isoformat"):
                health[key] = value.isoformat()
        health["updated_at"] = timezone.now().isoformat()
        try:
            cache.set(f"live_ws_health:{credential_id}", health, timeout=86400)
        except Exception:
            logger.exception("Could not publish WebSocket health for credential %s", credential_id)
        
    def start_processor(self, credential_id: int) -> bool:
        """
        Start WebSocket processor for a credential.
        
        Args:
            credential_id: Broker credential ID
            
        Returns:
            True if started successfully, False otherwise
        """
        from brokers.models import BrokerCredential

        with self.lock:
            if credential_id in self.active_processors:
                logger.warning(f"WebSocket processor already running for credential {credential_id}")
                return False
            
            try:
                credential = BrokerCredential.objects.get(id=credential_id)
                broker_session_id = self._latest_valid_session_id(credential_id)
                if broker_session_id is None:
                    self.connection_health[credential_id] = {
                        "status": "authentication_required",
                        "broker_session_id": None,
                        "reconnect_attempts": 0,
                        "last_error": "No valid broker session",
                    }
                    self._publish_health(credential_id)
                    logger.info("WebSocket for credential %s is waiting for broker authentication", credential_id)
                    return False

                processor = LiveWebSocketProcessor(credential)
                processor.start()
                
                self.active_processors[credential_id] = processor
                self.connection_health[credential_id] = {
                    "status": "connected",
                    "last_heartbeat": timezone.now(),
                    "connected_since": time.time(),
                    "reconnect_attempts": 0,
                    "broker_session_id": processor.auth_session_id or broker_session_id,
                    "last_error": None
                }
                self._publish_health(credential_id)
                
                logger.info(f"Started WebSocket processor for credential {credential_id}")
                return True
                
            except Exception as e:
                previous = self.connection_health.get(credential_id, {})
                self.connection_health[credential_id] = {
                    **previous,
                    "status": "disconnected",
                    "reconnect_attempts": int(previous.get("reconnect_attempts", 0)) + 1,
                    "last_reconnect_attempt": time.time(),
                    "last_error": str(e),
                }
                self._publish_health(credential_id)
                logger.exception(f"Failed to start WebSocket processor for credential {credential_id}: {e}")
                return False

    @staticmethod
    def _latest_valid_session_id(credential_id: int):
        from brokers.models import BrokerSession

        return BrokerSession.objects.filter(credential_id=credential_id, is_valid=True, token_expiry__gt=timezone.now()).order_by("-created_at").values_list("id", flat=True).first()
    
    def stop_processor(self, credential_id: int) -> None:
        """
        Stop WebSocket processor for a credential.
        
        Args:
            credential_id: Broker credential ID
        """
        with self.lock:
            if credential_id not in self.active_processors:
                return

            try:
                processor = self.active_processors[credential_id]
                processor.stop()
            except Exception as e:
                logger.exception(f"Error stopping WebSocket processor for credential {credential_id}: {e}")
            finally:
                self.active_processors.pop(credential_id, None)
                self.connection_health.pop(credential_id, None)
                try:
                    from django.core.cache import cache
                    cache.delete(f"live_ws_health:{credential_id}")
                except Exception:
                    logger.exception("Could not clear WebSocket health for credential %s", credential_id)
                logger.info(f"Stopped WebSocket processor for credential {credential_id}")
    
    def start_health_monitor(self) -> None:
        """Start health monitoring thread."""
        if self.running:
            logger.warning("Health monitor already running")
            return
        
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="WebSocketHealthMonitor"
        )
        self.health_check_thread.start()
        logger.info("WebSocket health monitor started")
    
    def stop_health_monitor(self) -> None:
        """Stop health monitoring thread."""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            logger.info("WebSocket health monitor stopped")
        self.health_check_thread = None
    
    def _health_check_loop(self) -> None:
        """Health check loop running in background thread."""
        # Let start_websocket perform its initial credential scan before the
        # recovery scan attempts to start any missing authenticated processors.
        time.sleep(self.health_check_interval)
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.exception(f"Error in health check loop: {e}")
                time.sleep(self.health_check_interval)
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all active processors."""
        with self.lock:
            for credential_id, processor in list(self.active_processors.items()):
                try:
                    health = self.connection_health.setdefault(credential_id, {})
                    broker_session_id = self._latest_valid_session_id(credential_id)
                    if broker_session_id is None:
                        logger.info("Broker session expired for credential %s; stopping its WebSocket until re-authentication", credential_id)
                        
                        self.stop_processor(credential_id)
                        self.connection_health[credential_id] = {
                            "status": "authentication_required",
                            "broker_session_id": None,
                            "reconnect_attempts": 0,
                            "last_error": "No valid broker session",
                        }
                        self._publish_health(credential_id)
                        continue

                    if str(health.get("broker_session_id")) != str(broker_session_id):
                        logger.info( "Broker session renewed for credential %s; restarting WebSocket processor", credential_id)
                        self.stop_processor(credential_id)
                        self.start_processor(credential_id)
                        continue

                    if not processor.is_healthy:
                        last_attempt = health.get("last_reconnect_attempt", 0)
                        attempts = int(health.get("reconnect_attempts", 0))
                        backoff = min(300, 5 * (2 ** min(attempts, 6)))
                        if time.time() - float(last_attempt or 0) < backoff:
                            continue
                        logger.warning(f"WebSocket processor for credential {credential_id} not running, attempting reconnect")
                        health["last_reconnect_attempt"] = time.time()
                        self._reconnect_processor(credential_id)
                    else:
                        health["last_heartbeat"] = timezone.now()
                        health["status"] = "connected"
                        if time.time() - float(health.get("connected_since", time.time())) >= 120:
                            health["reconnect_attempts"] = 0
                    self._publish_health(credential_id)
                        
                except Exception as e:
                    logger.exception(f"Error checking health for credential {credential_id}: {e}")

            self._start_authenticated_processors()

    def _start_authenticated_processors(self) -> None:
        """Start active, authenticated credentials not currently managed."""
        from brokers.models import BrokerCredential

        credentials = BrokerCredential.objects.filter(is_active=True, is_verified=True, sessions__is_valid=True, sessions__token_expiry__gt=timezone.now()).distinct()
        for credential in credentials:
            if credential.id in self.active_processors:
                continue
            health = self.connection_health.get(credential.id, {})
            attempts = int(health.get("reconnect_attempts", 0))
            backoff = min(300, 5 * (2 ** min(attempts, 6)))
            last_attempt = float(health.get("last_reconnect_attempt", 0) or 0)
            if time.time() - last_attempt < backoff:
                continue
            self.start_processor(credential.id)
    
    def _reconnect_processor(self, credential_id: int) -> None:
        """
        Attempt to reconnect a failed WebSocket processor.
        
        Args:
            credential_id: Broker credential ID
        """
        from brokers.models import BrokerCredential
        
        health = self.connection_health.get(credential_id, {})
        reconnect_attempts = health.get("reconnect_attempts", 0)
        
        if reconnect_attempts >= 5:
            logger.error(f"Max reconnect attempts reached for credential {credential_id}, switching to reconciliation mode")
            self._switch_to_reconciliation_mode(credential_id)
            return
        
        try:
            logger.info(f"Attempting reconnect {reconnect_attempts + 1}/5 for credential {credential_id}")
            
            # Stop existing processor
            if credential_id in self.active_processors:
                self.active_processors[credential_id].stop()
                del self.active_processors[credential_id]
            
            # Start new processor
            credential = BrokerCredential.objects.get(id=credential_id)
            processor = LiveWebSocketProcessor(credential)
            processor.start()
            
            self.active_processors[credential_id] = processor
            self.connection_health[credential_id] = {
                "status": "connected",
                "last_heartbeat": timezone.now(),
                "connected_since": time.time(),
                "reconnect_attempts": reconnect_attempts + 1,
                "broker_session_id": processor.auth_session_id or self._latest_valid_session_id(credential_id),
                "last_reconnect_attempt": time.time(),
                "last_error": None
            }
            self._publish_health(credential_id)
            
            logger.info(f"Successfully reconnected WebSocket for credential {credential_id}")
            
        except Exception as e:
            logger.exception(f"Reconnect failed for credential {credential_id}: {e}")
            self.connection_health[credential_id]["reconnect_attempts"] = reconnect_attempts + 1
            self.connection_health[credential_id]["last_error"] = str(e)
            self._publish_health(credential_id)
    
    def _switch_to_reconciliation_mode(self, credential_id: int) -> None:
        """
        Switch to reconciliation mode when WebSocket fails repeatedly.
        
        Args:
            credential_id: Broker credential ID
        """
        logger.warning(f"Switching to reconciliation mode for credential {credential_id}")
        try:
            from live_trading.tasks import reconcile_all_active_accounts
            reconcile_all_active_accounts.delay(credential_id=credential_id)
            health = self.connection_health.setdefault(credential_id, {})
            health["status"] = "reconciliation"
            self._publish_health(credential_id)
        except Exception as e:
            logger.exception("Could not schedule REST reconciliation for credential %s: %s", credential_id, e)
    
    def stop_all(self) -> None:
        """Stop all WebSocket processors and health monitor."""
        logger.info("Stopping all WebSocket processors")
        self.running = False

        for credential_id in list(self.active_processors.keys()):
            self.stop_processor(credential_id)

        self.stop_health_monitor()
        logger.info("All WebSocket processors stopped")
    
    def get_connection_status(self) -> Dict[int, Dict[str, Any]]:
        """
        Get connection status for all active processors.
        
        Returns:
            Dictionary mapping credential_id to connection health info
        """
        with self.lock:
            return self.connection_health.copy()


# Global instance
_websocket_manager = WebSocketConnectionManager()
