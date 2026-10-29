"""FYERS V3 authentication and trading adapter. Vendor keys stay in this module."""
import re
import time
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from fyers_apiv3 import fyersModel
from rest_framework import serializers

from common.enums import BrokerName, OrderStatus, Side
from .base import BROKER_SESSION_EXPIRED_CACHE_KEY, BaseBrokerAdapter
from .models import BrokerSession


class FyersConfigurationSerializer(serializers.Serializer):
    client_id = serializers.RegexField(r"^[A-Za-z0-9-]+$", max_length=120, label="App ID")
    api_secret = serializers.CharField(
        required=False, allow_blank=True, write_only=True, trim_whitespace=True, max_length=512,
        style={"input_type": "password"}, label="App Secret",
    )


class FyersAuth:
    """Individual-app OAuth, parameterized for the source or an owner's trading app."""
    def __init__(self, client_id: str, secret: str, redirect_uri: str):
        if not client_id or not secret or not redirect_uri:
            raise ValueError("Configure the FYERS App ID, App Secret and redirect URI before connecting.")
        self.client_id = client_id
        self.secret = secret
        self.redirect_uri = redirect_uri

    def _session_model(self, state: str):
        return fyersModel.SessionModel(
            client_id=self.client_id, secret_key=self.secret, redirect_uri=self.redirect_uri,
            response_type="code", grant_type="authorization_code", state=state,
        )

    def authorization_url(self, state: str) -> str:
        return self._session_model(state).generate_authcode()

    def exchange_code(self, auth_code: str) -> dict:
        session = self._session_model("")
        session.set_token(auth_code)
        response = session.generate_token()
        if response["s"] != "ok":
            raise ValueError(response["message"])
        # FYERS documents a daily 06:30 IST boundary, not an expires_in field.
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        expiry = now.replace(hour=6, minute=30, second=0, microsecond=0)
        if expiry <= now:
            expiry += timedelta(days=1)
        return {"access_token": response["access_token"], "expires_at": expiry}


class FyersAdapter(BaseBrokerAdapter):
    broker_name = BrokerName.FYERS
    display_name = "Fyers"
    configuration_serializer = FyersConfigurationSerializer
    ORDER_SIDES = {1: Side.BUY, -1: Side.SELL}
    ORDER_STATUSES = {
        1: OrderStatus.CANCELLED, 2: OrderStatus.FILLED, 4: OrderStatus.PLACED,
        5: OrderStatus.REJECTED, 6: OrderStatus.PENDING, 7: OrderStatus.EXPIRED,
    }
    API_URL = "https://api-t1.fyers.in/api/v3"

    @staticmethod
    def connection_details() -> dict:
        uri = settings.BROKER_FYERS_REDIRECT_URI
        parts = urlsplit(uri)
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment or parts.path != reverse("fyers_broker_callback")
                or (not settings.DEBUG and parts.scheme != "https")):
            raise ValueError("Configure the exact FYERS trading callback URL; production requires HTTPS.")
        return {"redirect_uri": uri}

    def _auth(self):
        return FyersAuth(self.credential.client_id, self.credential.api_secret, self.connection_details()["redirect_uri"])

    def _log_response(self, endpoint, request, response, started_at):
        self._log(endpoint, request, response, started_at=started_at,
                  status_code=400 if response.get("s") == "error" else 200,
                  error_message=response["message"] if response.get("s") == "error" else "")

    def _request(self, method: str, path: str, session, data=None) -> dict:
        # The SDK hides transport errors and leaves GET calls without timeouts.
        # Bound every broker call; uncertain mutations must reach reconciliation.
        try:
            response = requests.request(
                method, self.API_URL + path, json=data,
                headers={"Authorization": f"{self.credential.client_id}:{session.access_token}", "version": "3"},
                timeout=(5, 10),
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if method == "GET":
                raise ValueError("FYERS account data is temporarily unavailable. Retry after the connection recovers.") from exc
            raise

    def generate_auth_url(self, state: str) -> str:
        return self._auth().authorization_url(state)

    def exchange_auth_code(self, auth_code: str):
        token = self._auth().exchange_code(auth_code)
        BrokerSession.objects.filter(credential=self.credential, is_valid=True).update(is_valid=False)
        session = BrokerSession.objects.create(
            credential=self.credential, access_token=token["access_token"], token_expiry=token["expires_at"],
        )
        cache.delete(BROKER_SESSION_EXPIRED_CACHE_KEY.format(credential_id=self.credential.pk))
        return session

    def get_profile(self) -> dict:
        started_at = time.perf_counter()
        response = self._request("GET", "/profile", self.get_session())
        # Do not persist masked personal/security fields in API logs.
        if response["s"] != "ok":
            raise ValueError(response["message"])
        row = response["data"]
        profile = {"name": row["name"], "account_reference": row["fy_id"],
                   "email": row["email_id"], "mobile": row["mobile_number"]}
        self._log("fyers.get_profile", {}, {"verified": True}, started_at=started_at)
        return profile

    def get_funds(self) -> dict:
        started_at = time.perf_counter()
        response = self._request("GET", "/funds", self.get_session())
        self._log_response("fyers.funds", {}, response, started_at)
        if response["s"] != "ok":
            raise ValueError(response["message"])
        # Match documented ledger headings; zero and negative balances are valid.
        ledger = {row["title"]: Decimal(str(row["equityAmount"])) for row in response["fund_limit"]}
        return {
            "cash_balance": ledger["Clear Balance"], "available_margin": ledger["Available Balance"],
            "used_margin": ledger["Utilized Amount"], "collateral": ledger["Collaterals"],
            "net_equity": ledger["Total Balance"], "realized_pnl": ledger["Realized Profit and Loss"],
            "withdrawable_balance": None, "unrealized_pnl": None, "raw_payload": response,
        }

    def normalize_order(self, row: dict) -> dict:
        """Consume the documented REST / Python SDK camel-case order schema."""
        ordered_at = datetime.strptime(row["orderDateTime"], "%d-%b-%Y %H:%M:%S").replace(
            tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(datetime_timezone.utc)
        # This raw documented OMS clock is retained by our socket's SDK mapper.
        event_epoch = row.get("brokerUpdateTime")
        event_at = datetime.fromtimestamp(event_epoch, datetime_timezone.utc) if event_epoch else None
        return {
            "broker_order_id": row["id"], "exchange_order_id": row.get("exchOrdId", ""),
            "order_tag": row.get("orderTag", "").removeprefix("1:"),
            "symbol": row["symbol"], "product_type": row["productType"], "side": self.ORDER_SIDES[row["side"]],
            "quantity": row["qty"], "filled_quantity": row.get("filledQty", 0),
            "pending_quantity": row["remainingQuantity"],
            "avg_fill_price": Decimal(str(row.get("tradedPrice", 0))),
            "status": self.ORDER_STATUSES.get(row["status"], "UNKNOWN"),
            "rejection_reason": row.get("message", ""), "broker_ordered_at": ordered_at.isoformat(),
            "broker_updated_at": event_at.isoformat() if event_at else None,
        }

    def get_orderbook(self) -> list[dict]:
        started_at = time.perf_counter()
        response = self._request("GET", "/orders", self.get_session())
        self._log_response("fyers.orderbook", {}, response, started_at)
        if response["s"] != "ok":
            raise ValueError(response["message"])
        return [self.normalize_order(row) for row in response["orderBook"]]

    def place_order(self, payload: dict, session) -> dict:
        self.validate_order(payload)
        if not re.fullmatch(r"[A-Za-z0-9]{1,30}", payload["order_tag"]):
            raise ValueError("FYERS order tags must contain 1 to 30 letters or digits.")
        request = {
            "symbol": payload["instrument"], "qty": payload["quantity"], "type": 2,
            "side": 1 if payload["side"] == Side.BUY else -1, "productType": payload["product_type"],
            "limitPrice": 0, "stopPrice": 0, "validity": "DAY", "disclosedQty": 0,
            "offlineOrder": False, "orderTag": payload["order_tag"], "isSliceOrder": False,
        }
        started_at = time.perf_counter()
        response = self._request("POST", "/orders/sync", session, request)
        self._log_response("fyers.place_order", request, response, started_at)
        status = "UNKNOWN"
        if response.get("code") != 201:
            if response.get("s") == "ok" and response.get("id"):
                status = OrderStatus.PLACED
            elif response.get("s") == "error":
                status = OrderStatus.REJECTED
        return {"broker_order_id": response.get("id", ""), "exchange_order_id": "",
                "status": status, "message": response.get("message", ""), "raw_response": response}

    def cancel_order(self, broker_order_id: str) -> dict:
        started_at = time.perf_counter()
        response = self._request("DELETE", "/orders/sync", self.get_session(), {"id": broker_order_id})
        self._log_response("fyers.cancel_order", {"id": broker_order_id}, response, started_at)
        return {"broker_order_id": broker_order_id, "accepted": response["s"] == "ok" and response["code"] != 201,
                "message": response["message"]}

    def create_order_stream(self):
        from .websocket.fyers_websocket import FyersOrderWebSocket
        return FyersOrderWebSocket(self)
