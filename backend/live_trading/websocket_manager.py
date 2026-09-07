"""
WebSocket Connection Manager
Manages WebSocket connections for live trading with health monitoring and auto-reconnection.
"""

import logging
import threading
import time
from typing import Dict, Optional
from django.utils import timezone

from brokers.websocket.factory import BrokerWebSocketFactory
from live_trading.websocket_processor import LiveWebSocketProcessor
from live_trading.reconciliation_service import BrokerReconciliationService

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
        self.lock = threading.Lock()
        
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
                processor = LiveWebSocketProcessor(credential)
                processor.start()
                
                self.active_processors[credential_id] = processor
                self.connection_health[credential_id] = {
                    "status": "connected",
                    "last_heartbeat": timezone.now(),
                    "reconnect_attempts": 0,
                    "last_error": None
                }
                
                logger.info(f"Started WebSocket processor for credential {credential_id}")
                return True
                
            except Exception as e:
                logger.exception(f"Failed to start WebSocket processor for credential {credential_id}: {e}")
                return False
    
    def stop_processor(self, credential_id: int) -> None:
        """
        Stop WebSocket processor for a credential.
        
        Args:
            credential_id: Broker credential ID
        """
        with self.lock:
            if credential_id in self.active_processors:
                try:
                    processor = self.active_processors[credential_id]
                    processor.stop()
                    del self.active_processors[credential_id]
                    del self.connection_health[credential_id]
                    logger.info(f"Stopped WebSocket processor for credential {credential_id}")
                except Exception as e:
                    logger.exception(f"Error stopping WebSocket processor for credential {credential_id}: {e}")
    
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
    
    def _health_check_loop(self) -> None:
        """Health check loop running in background thread."""
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
                    # Check if processor is still connected
                    if not processor.is_running:
                        logger.warning(f"WebSocket processor for credential {credential_id} not running, attempting reconnect")
                        self._reconnect_processor(credential_id)
                    else:
                        # Update heartbeat
                        self.connection_health[credential_id]["last_heartbeat"] = timezone.now()
                        
                except Exception as e:
                    logger.exception(f"Error checking health for credential {credential_id}: {e}")
    
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
                "reconnect_attempts": 0,
                "last_error": None
            }
            
            logger.info(f"Successfully reconnected WebSocket for credential {credential_id}")
            
        except Exception as e:
            logger.exception(f"Reconnect failed for credential {credential_id}: {e}")
            self.connection_health[credential_id]["reconnect_attempts"] = reconnect_attempts + 1
            self.connection_health[credential_id]["last_error"] = str(e)
    
    def _switch_to_reconciliation_mode(self, credential_id: int) -> None:
        """
        Switch to reconciliation mode when WebSocket fails repeatedly.
        
        Args:
            credential_id: Broker credential ID
        """
        from brokers.models import BrokerCredential
        
        logger.warning(f"Switching to reconciliation mode for credential {credential_id}")
        
        try:
            credential = BrokerCredential.objects.get(id=credential_id)
            reconciliation_service = BrokerReconciliationService(credential)
            
            # Perform immediate reconciliation
            reconciliation_service.reconcile_orders()
            reconciliation_service.reconcile_positions()
            
            # Schedule periodic reconciliation
            # (This would be implemented with Celery Beat or similar)
            logger.info(f"Reconciliation completed for credential {credential_id}")
            
        except Exception as e:
            logger.exception(f"Error in reconciliation mode for credential {credential_id}: {e}")
    
    def stop_all(self) -> None:
        """Stop all WebSocket processors and health monitor."""
        logger.info("Stopping all WebSocket processors")
        
        with self.lock:
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
