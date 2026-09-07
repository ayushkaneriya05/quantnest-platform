"""
Factory for creating broker WebSocket instances.
Provides a unified interface to instantiate broker-specific WebSocket implementations.
"""

import logging
from common.enums import BrokerName

from .base_websocket import BaseBrokerWebSocket
from .fyers_websocket import FyersOrderWebSocket
from .paper_simulation import PaperWebSocketSimulator

logger = logging.getLogger(__name__)


class BrokerWebSocketFactory:
    """
    Factory for creating broker WebSocket instances.
    
    This factory pattern makes it easy to add new broker implementations
    without modifying the core execution services.
    """
    
    # Broker WebSocket class mapping
    BROKER_WEBSOCKET_CLASSES = {
        BrokerName.FYERS: FyersOrderWebSocket,
        # Add new brokers here as they are implemented:
        # BrokerName.ZERODHA: ZerodhaOrderWebSocket,
        # BrokerName.ANGEL: AngelOrderWebSocket,
    }
    
    @staticmethod
    def create(credential, account=None):
        """
        Create a broker WebSocket instance based on credential.
        
        Args:
            credential: BrokerCredential instance
            account: Optional PaperAccount instance for paper trading simulation
            
        Returns:
            Instance of BaseBrokerWebSocket subclass
            
        Raises:
            ValueError: If broker is not supported
        """
        broker_name = credential.broker_name
        
        # Check if this is for paper trading simulation
        if account is not None:
            logger.info(f"Creating paper WebSocket simulator for account {account.id}")
            return PaperWebSocketSimulator(account)
        
        # Get broker-specific WebSocket class
        websocket_class = BrokerWebSocketFactory.BROKER_WEBSOCKET_CLASSES.get(broker_name)
        
        if websocket_class is None:
            supported_brokers = list(BrokerWebSocketFactory.BROKER_WEBSOCKET_CLASSES.keys())
            raise ValueError(
                f"Broker '{broker_name}' WebSocket is not supported. "
                f"Supported brokers: {supported_brokers}"
            )
        
        logger.info(f"Creating {broker_name} WebSocket for credential {credential.id}")
        return websocket_class(credential)
    
    @staticmethod
    def get_supported_brokers():
        """
        Get list of supported brokers for WebSocket integration.
        
        Returns:
            List of broker names that have WebSocket implementations
        """
        return list(BrokerWebSocketFactory.BROKER_WEBSOCKET_CLASSES.keys())
    
    @staticmethod
    def is_broker_supported(broker_name: str) -> bool:
        """
        Check if a broker has WebSocket support.
        
        Args:
            broker_name: Name of the broker to check
            
        Returns:
            True if broker has WebSocket support, False otherwise
        """
        return broker_name in BrokerWebSocketFactory.BROKER_WEBSOCKET_CLASSES
