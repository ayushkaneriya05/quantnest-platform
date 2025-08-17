# backend/trading/order_routing.py
"""
Adapter to interact with Fyers REST (via fyers_apiv3) for optional live order routing.
For paper trading we simulate executions internally; this adapter is provided if you
later want to place live orders or to query market snapshots via the SDK.
"""

import os
import logging
from fyers_apiv3 import fyersModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
FYERS_SECRET = os.getenv("FYERS_SECRET")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")

def _get_fyers_client():
    cfg = {"client_id": FYERS_CLIENT_ID, "secret_key": FYERS_SECRET, "access_token": FYERS_ACCESS_TOKEN}
    return fyersModel.FyersModel(cfg)

class FyersAdapter:
    def __init__(self):
        self.client = _get_fyers_client()

    def historical(self, symbol, resolution="1", start_ts=None, end_ts=None):
        fy_sym = symbol if ":" in symbol else f"NSE:{symbol}-EQ"
        params = {"symbol": fy_sym, "resolution": str(resolution), "date_format": "1"}
        if start_ts:
            params["range_from"] = str(int(start_ts))
        if end_ts:
            params["range_to"] = str(int(end_ts))
        return self.client.history(params)

    def quotes(self, symbols):
        """
        Get quotes. symbols: list of fyers formatted symbols like ["NSE:RELIANCE-EQ"]
        """
        if not isinstance(symbols, (list, tuple)):
            raise ValueError("symbols must be a list")
        sym_str = ",".join(symbols)
        params = {"symbols": sym_str}
        return self.client.quotes(params)

    def place_order(self, payload):
        """
        Place an order via fyers REST. Payload structure depends on SDK version.
        This method is intentionally conservative. Use only in live routing.
        """
        return self.client.place_order(payload)
