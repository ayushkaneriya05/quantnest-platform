"""Minimal contract for broker order streams."""
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

logger = logging.getLogger(__name__)


class BaseBrokerWebSocket(ABC):
    def __init__(self, adapter):
        self.adapter = adapter
        self.credential = adapter.credential
        self.auth_session_id = None
        self.order_callbacks = []
        self.is_connected = False
        self.is_subscribed = False

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def subscribe(self) -> None:
        pass

    def on_order_update(self, callback: Callable[[dict], None]) -> None:
        self.order_callbacks.append(callback)

    def _emit_order_update(self, order: dict) -> None:
        for callback in self.order_callbacks:
            try:
                callback(order)
            except Exception:
                logger.exception("Broker order callback failed")
