# marketdata/fyers_ws_client.py
import json
from fyers_apiv3 import fyersModel
from marketdata.utils import get_active_fyers_access_token

class FyersWebSocketClient:
    def __init__(self, client_id):
        self.client_id = client_id
        self.access_token = get_active_fyers_access_token()
        self.ws = None

    def connect(self):
        self.ws = fyersModel.FyersDataSocket(
            access_token=f"{self.client_id}:{self.access_token}",
            log_path="./logs"
        )
        return self.ws

    def subscribe(self, symbols, data_type="SymbolUpdate"):
        if not self.ws:
            self.connect()
        self.ws.subscribe(symbols=symbols, data_type=data_type)

    def unsubscribe(self, symbols, data_type="SymbolUpdate"):
        if self.ws:
            self.ws.unsubscribe(symbols=symbols, data_type=data_type)

    def close(self):
        if self.ws:
            self.ws.close_connection()
