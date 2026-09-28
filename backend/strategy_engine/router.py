import logging
import uuid
from dataclasses import dataclass, asdict, field
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
    intent: str = "ENTRY"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return asdict(self)
    
class StrategyOrderRouter:
    """Publish durable order requests to a scope-specific Redis Stream."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(StrategyOrderRouter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        logger.info("OrderRouter initialized with durable Redis Streams transport")

    def publish_order(self, request: OrderRequest):
        """
        Adds the request to its live or paper stream. XADD is the durable handoff.
        """
        from strategy_engine.order_queue import publish_order
        request_id = publish_order(request)
        logger.info("Queued %s order request %s for instrument %s", request.scope, request_id, request.instrument_id)
        return request_id
