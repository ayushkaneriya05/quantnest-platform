# backend/marketdata/fyers_ws_client.py

import logging
from fyers_apiv3.FyersWebsocket import data_ws
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class FyersWebsocketClient:
    """
    A client for connecting to the Fyers WebSocket API to stream real-time market data.
    """

    def __init__(self, on_message=None, on_error=None, on_open=None, on_close=None):
        """
        Initializes the FyersWebsocketClient.

        Args:
            on_message (function): Callback function to handle incoming messages.
            on_error (function): Callback function to handle errors.
            on_open (function): Callback function to handle the connection opening.
            on_close (function): Callback function to handle the connection closing.
        """
        self.client_id = settings.FYERS_CLIENT_ID
        self.fyers_socket = None
        self.on_message_callback = on_message
        self.on_error_callback = on_error
        self.on_open_callback = on_open
        self.on_close_callback = on_close

    def _on_message(self, message):
        """
        Internal message handler that calls the provided callback.
        """
        if self.on_message_callback:
            self.on_message_callback(message)

    def _on_error(self, message):
        """
        Internal error handler that logs the error and calls the provided callback.
        """
        logger.error(f"Fyers WebSocket Error: {message}")
        if self.on_error_callback:
            self.on_error_callback(message)

    def _on_open(self):
        """
        Internal open handler that logs the connection and calls the provided callback.
        """
        logger.info("Fyers WebSocket connection opened.")
        if self.on_open_callback:
            self.on_open_callback()

    def _on_close(self, message):
        """
        Internal close handler that logs the disconnection and calls the provided callback.
        """
        logger.warning(f"Fyers WebSocket connection closed: {message}")
        if self.on_close_callback:
            self.on_close_callback(message)

    def connect(self, access_token):
        """
        Establishes a connection to the Fyers WebSocket.

        Args:
            access_token (str): The raw access token obtained from the Fyers API.
        """
        if not access_token:
            logger.error("Cannot connect to Fyers WebSocket without an access token.")
            return

        # ✅ FIXED: The access token must be in the format "CLIENT_ID:ACCESS_TOKEN".
        # This is the critical change based on the official Fyers API v3 documentation.
        formatted_token = f"{self.client_id}:{access_token}"

        self.fyers_socket = data_ws.FyersDataSocket(
            access_token=formatted_token,
            log_path="",  # Disables file logging for cleaner output
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_connect=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
        )
        self.fyers_socket.connect()
        logger.info("Attempting to connect to Fyers WebSocket...")

    def subscribe(self, symbols, data_type="symbolUpdate"):
        """
        Subscribes to real-time data for a list of symbols.

        Args:
            symbols (list): A list of symbols to subscribe to (e.g., ["NSE:SBIN-EQ"]).
            data_type (str): The type of data to subscribe to ('symbolUpdate' or 'lite').
        """
        if self.fyers_socket:
            logger.info(f"Subscribing to symbols: {symbols} with data_type: {data_type}")
            self.fyers_socket.subscribe(symbols=symbols, data_type=data_type)
        else:
            logger.error("Cannot subscribe, WebSocket is not connected.")

    def unsubscribe(self, symbols):
        """
        Unsubscribes from real-time data for a list of symbols.

        Args:
            symbols (list): A list of symbols to unsubscribe from.
        """
        if self.fyers_socket:
            logger.info(f"Unsubscribing from symbols: {symbols}")
            self.fyers_socket.unsubscribe(symbols=symbols)
        else:
            logger.error("Cannot unsubscribe, WebSocket is not connected.")

    def close(self):
        """
        Closes the WebSocket connection.
        """
        if self.fyers_socket:
            self.fyers_socket.close_connection()
            logger.info("Fyers WebSocket connection explicitly closed.")

