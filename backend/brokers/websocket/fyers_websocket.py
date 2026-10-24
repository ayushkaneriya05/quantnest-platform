"""FYERS order-only stream using the same normalization as REST."""
import logging

from django.conf import settings
from fyers_apiv3.FyersWebsocket import order_ws

from .base_websocket import BaseBrokerWebSocket

logger = logging.getLogger(__name__)


class FyersOrderWebSocket(BaseBrokerWebSocket):
    def __init__(self, adapter):
        super().__init__(adapter)
        self.socket = None

    def connect(self) -> None:
        session = self.adapter.get_session()
        self.auth_session_id = session.pk
        self.socket = order_ws.FyersOrderSocket(
            access_token=f"{self.credential.client_id}:{session.access_token}",
            log_path=str(settings.BASE_DIR / "logs"),
            on_orders=self._on_order_message,
            on_connect=self._on_connect,
            on_close=self._on_close,
            on_error=self._on_error,
            reconnect=False,  # The supervised manager owns retries and authentication.
        )
        # The pinned SDK drops this broker event clock from its default parsed row.
        self.socket.order_mapper["update_time_epoch_oms"] = "brokerUpdateTime"
        self.socket.connect()

    def disconnect(self) -> None:
        socket = self.socket
        if socket is None:
            return
        try:
            socket.close_connection()
        except AttributeError:
            # The SDK can fail before its worker/ping threads are initialized.
            logger.debug("FYERS order socket closed during startup credential=%s", self.credential.pk)
        finally:
            self.socket = None
            self.is_connected = self.is_subscribed = False

    def _on_connect(self):
        self.is_connected = True
        self.subscribe()

    def _on_close(self, message):
        self.is_connected = self.is_subscribed = False

    def _on_error(self, message):
        self.is_connected = self.is_subscribed = False
        logger.warning("FYERS order socket error credential=%s", self.credential.pk)

    def subscribe(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Connect the broker order stream before subscribing.")
        self.socket.subscribe(data_type="OnOrders")
        self.is_subscribed = True

    def _on_order_message(self, message: dict) -> None:
        if message.get("s") == "ok" and message.get("orders"):
            try:
                self._emit_order_update(self.adapter.normalize_order(message["orders"]))
            except Exception:
                logger.exception("Invalid FYERS order update credential=%s", self.credential.pk)
