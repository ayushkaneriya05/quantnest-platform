import zmq
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class OrderRequest:
    session_id: str
    strategy_id: str
    instrument_id: int
    side: str
    qty: int
    order_type: str
    scope: str # "LIVE" or "PAPER"
    target_price: float
    reason: Optional[str] = None
    
class StrategyOrderRouter:
    """
    ZeroMQ Publisher for routing order requests from the Multiprocessing workers
    to the central Paper/Live execution services.
    Uses tcp:// for ultra-fast local socket IPC (since ipc:// is not fully supported on Windows).
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(StrategyOrderRouter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, live_endpoint="tcp://127.0.0.1:5555", paper_endpoint="tcp://127.0.0.1:5556"):
        if self._initialized:
            return
            
        self.live_endpoint = live_endpoint
        self.paper_endpoint = paper_endpoint
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        
        # In a multiprocessing environment, all worker PUB sockets MUST connect.
        # The central subscriber (e.g., Execution Service) MUST bind to its SUB socket.
        self.socket.connect(self.live_endpoint)
        self.socket.connect(self.paper_endpoint)
        time.sleep(0.1)  # Allow ZMQ connection setup (slow joiner problem)
        logger.info(f"OrderRouter PUB connected to {self.live_endpoint} and {self.paper_endpoint}")
            
        self._initialized = True

    def publish_order(self, request: OrderRequest):
        """
        Publishes the order onto the ZeroMQ bus.
        The topic is the scope (e.g., "LIVE" or "PAPER") so subscribers can filter.
        """
        topic = request.scope.encode('utf-8')
        message = json.dumps(asdict(request)).encode('utf-8')
        self.socket.send_multipart([topic, message])
        logger.info(f"Published {request.scope} OrderRequest for {request.instrument_id}")
