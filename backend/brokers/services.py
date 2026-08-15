import logging
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from common.enums import BrokerName, FyersOrderSide, FyersOrderType, OrderStatus, NotificationType, Severity
from notifications.services import NotificationService

from .models import BrokerAPILog, BrokerCredential, BrokerFundsSnapshot, BrokerSession, OrderSettings

try:
    from fyers_apiv3 import fyersModel
except Exception:
    fyersModel = None



logger = logging.getLogger(__name__)


def notify_broker_session_expired(credential, reason=None):
    cache_key = f"broker_session_expired_notification_{credential.id}"
    if cache.get(cache_key):
        return
    NotificationService.notify(
        user=credential.user,
        title="Broker Session Expired",
        message=reason or f"Broker session for '{credential.label}' has expired. Reconnect your broker account to continue live trading.",
        notification_type=NotificationType.SYSTEM_ALERT,
        severity=Severity.CRITICAL,
        data={"broker_credential_id": str(credential.id), "module": "broker"}
    )
    cache.set(cache_key, True, 3600)


BROKER_CATALOG = {
    BrokerName.FYERS: {
        "broker_name": BrokerName.FYERS,
        "display_name": "Fyers",
        "description": "Connect a Fyers trading account for live order execution and position sync.",
        "auth_type": "OAUTH_REDIRECT",
        "enabled": True,
        "logo_text": "FY",
    },
    BrokerName.ZERODHA: {
        "broker_name": BrokerName.ZERODHA,
        "display_name": "Zerodha",
        "description": "Adapter scaffold is ready, broker onboarding flow is not enabled yet.",
        "auth_type": "OAUTH_REDIRECT",
        "enabled": False,
        "logo_text": "ZD",
    },
    BrokerName.ANGEL: {
        "broker_name": BrokerName.ANGEL,
        "display_name": "Angel One",
        "description": "Adapter scaffold is ready, broker onboarding flow is not enabled yet.",
        "auth_type": "OAUTH_REDIRECT",
        "enabled": False,
        "logo_text": "AG",
    },
}

FYERS_PLATFORM_CLIENT_REF = "FYERS_PLATFORM_APP"


class BrokerConnectionConfigError(ValueError):
    pass


class BaseBrokerAdapter:
    broker_name = None

    def __init__(self, credential):
        self.credential = credential

    @staticmethod
    def _json_safe(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {
                str(item_key): BaseBrokerAdapter._json_safe(item_value)
                for item_key, item_value in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [BaseBrokerAdapter._json_safe(item) for item in value]
        return str(value)

    def _log(self, endpoint, request_data=None, response_data=None, status_code=200, error_message="", started_at=None):
        latency_ms = 0
        if started_at is not None:
            latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        BrokerAPILog.objects.create(
            credential=self.credential,
            endpoint=endpoint,
            request_data=self._json_safe(request_data or {}),
            response_data=self._json_safe(response_data or {}),
            status_code=status_code,
            latency_ms=latency_ms,
            error_message=error_message,
        )

    def verify(self):
        started_at = time.perf_counter()
        ok = bool(self.credential.client_id and self.credential.api_key)
        response = {
            "verified": ok,
            "broker": self.broker_name,
            "message": "Credential verified" if ok else "Client ID and API key are required",
        }
        self._log("verify", {"client_id": self.credential.client_id}, response, 200 if ok else 400, response["message"], started_at)
        return response

    def create_session(self):
        started_at = time.perf_counter()
        token = f"{self.broker_name.lower()}_{uuid.uuid4().hex}"
        session = BrokerSession.objects.create(
            credential=self.credential,
            access_token=token,
            refresh_token=uuid.uuid4().hex,
            token_expiry=timezone.now() + timedelta(hours=12),
            is_valid=True,
        )
        self._log("create_session", {"credential_id": self.credential.id}, {"session_id": session.id}, started_at=started_at)
        return session

    def generate_auth_url(self):
        return None

    def exchange_auth_code(self, auth_code):
        return self.create_session()

    def get_profile(self):
        return {"s": "ok", "name": self.credential.label or self.credential.client_id}

    def get_funds(self):
        return {"s": "ok", "fund_limit": []}

    def get_orderbook(self):
        return {"s": "ok", "orderBook": []}

    def get_positions(self):
        return {"s": "ok", "netPositions": []}

    def place_order(self, payload):
        started_at = time.perf_counter()
        broker_order_id = f"{self.broker_name[:3]}-{uuid.uuid4().hex[:14].upper()}"
        response = {
            "broker_order_id": broker_order_id,
            "exchange_order_id": f"EX-{uuid.uuid4().hex[:12].upper()}",
            "status": OrderStatus.FILLED,
            "filled_quantity": int(payload.get("quantity") or 0),
            "avg_fill_price": str(payload.get("price") or payload.get("fallback_price") or 0),
        }
        self._log("place_order", payload, response, started_at=started_at)
        return response

    def cancel_order(self, broker_order_id):
        started_at = time.perf_counter()
        response = {"broker_order_id": broker_order_id, "status": OrderStatus.CANCELLED}
        self._log("cancel_order", {"broker_order_id": broker_order_id}, response, started_at=started_at)
        return response


class ZerodhaAdapter(BaseBrokerAdapter):
    broker_name = BrokerName.ZERODHA



class FyersAdapter(BaseBrokerAdapter):
    broker_name = BrokerName.FYERS

    def _client_id(self):
        return getattr(settings, "BROKER_FYERS_CLIENT_ID", "") or getattr(settings, "FYERS_CLIENT_ID", "")

    def _secret_key(self):
        return getattr(settings, "BROKER_FYERS_SECRET", "") or getattr(settings, "FYERS_SECRET", "")

    def _redirect_uri(self):
        return (
            getattr(settings, "BROKER_FYERS_REDIRECT_URI", "")
            or f"{getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')}/api/v1/brokers/credentials/fyers/callback/"
        )

    def _session_model(self, state=None):
        if fyersModel is None:
            raise RuntimeError("fyers_apiv3 is not installed")
        return fyersModel.SessionModel(
            client_id=self._client_id(),
            secret_key=self._secret_key(),
            redirect_uri=self._redirect_uri(),
            response_type="code",
            grant_type="authorization_code",
            state=state,
        )

    def _latest_session(self):
        return self.credential.sessions.filter(is_valid=True).order_by("-created_at").first()

    def _sdk_client(self, session=None):
        if fyersModel is None:
            raise RuntimeError("fyers_apiv3 is not installed")
        session = session or self._latest_session()
        if not session:
            raise ValueError("No valid Fyers session available. Exchange an auth code first.")
        if session.token_expiry <= timezone.now() or not session.is_valid:
            session.is_valid = False
            session.save(update_fields=["is_valid", "updated_at"])
            notify_broker_session_expired(self.credential)
            raise ValueError("Fyers trading session expired. Reconnect your broker account to continue.")
        return fyersModel.FyersModel(
            client_id=self._client_id(),
            token=session.access_token,
            is_async=False,
            log_path=str(settings.BASE_DIR / "logs"),
        )

    def generate_auth_url(self):
        started_at = time.perf_counter()
        if not self._client_id() or not self._secret_key() or not self._redirect_uri():
            raise BrokerConnectionConfigError(
                "Fyers trading app config is missing. Set BROKER_FYERS_CLIENT_ID, BROKER_FYERS_SECRET, and BROKER_FYERS_REDIRECT_URI."
            )
        signed_state = signing.dumps(
            {
                "user_id": self.credential.user_id,
                "credential_id": self.credential.id,
                "broker_name": self.broker_name,
            },
            salt="broker-oauth-state",
        )
        auth_url = self._session_model(state=signed_state).generate_authcode()
        self._log("fyers.generate_auth_url", {"client_id": self._client_id()}, {"auth_url": auth_url}, started_at=started_at)
        return auth_url

    def verify(self):
        started_at = time.perf_counter()
        if not self._client_id() or not self._secret_key() or not self._redirect_uri():
            response = {
                "verified": False,
                "broker": self.broker_name,
                "message": "Fyers client_id, secret_key/api_secret, and redirect URI are required",
            }
            self._log("fyers.verify_config", {"client_id": self._client_id()}, response, 400, response["message"], started_at)
            return response

        session = self._latest_session()
        if session and session.token_expiry > timezone.now() and session.is_valid:
            try:
                profile = self._sdk_client(session).get_profile()
                ok = profile.get("s") == "ok"
                response = {
                    "verified": ok,
                    "broker": self.broker_name,
                    "message": profile.get("message") or ("Fyers session verified" if ok else "Fyers profile check failed"),
                    "profile": profile,
                }
                self._log("fyers.verify_profile", {"session_id": session.id}, response, 200 if ok else 400, response["message"], started_at)
                return response
            except Exception as exc:
                self._log("fyers.verify_profile", {"session_id": session.id}, {}, 400, str(exc), started_at)

        try:
            auth_url = self._session_model().generate_authcode()
            response = {
                "verified": False,
                "broker": self.broker_name,
                "message": "Fyers app config looks valid. Complete OAuth login and exchange auth code to verify this broker account.",
                "auth_url": auth_url,
            }
            self._log("fyers.verify_auth_url", {"client_id": self._client_id()}, {"auth_url": auth_url}, started_at=started_at)
            return response
        except Exception as exc:
            response = {"verified": False, "broker": self.broker_name, "message": str(exc)}
            self._log("fyers.verify_auth_url", {"client_id": self._client_id()}, {}, 500, str(exc), started_at)
            return response

    def exchange_auth_code(self, auth_code):
        started_at = time.perf_counter()
        if not auth_code:
            raise ValueError("Fyers auth_code is required")
        session_model = self._session_model()
        session_model.set_token(auth_code)
        try:
            token_resp = session_model.generate_token()
        except Exception as exc:
            self._log(
                "fyers.exchange_auth_code",
                {"client_id": self._client_id()},
                {},
                500,
                f"Token exchange request failed: {exc}",
                started_at,
            )
            raise ValueError(f"Fyers token exchange request failed: {exc}") from exc
        access_token = token_resp.get("access_token") or token_resp.get("accessToken")
        if not access_token:
            message = token_resp.get("message") or "Fyers token exchange failed"
            self._log("fyers.exchange_auth_code", {"client_id": self._client_id()}, token_resp, 400, message, started_at)
            raise ValueError(message)

        local_now = timezone.localtime(timezone.now())
        expires_at = local_now.replace(hour=23, minute=59, second=59, microsecond=999999)
        BrokerSession.objects.filter(credential=self.credential, is_valid=True).update(is_valid=False)
        session = BrokerSession.objects.create(
            credential=self.credential,
            access_token=access_token,
            refresh_token=token_resp.get("refresh_token") or token_resp.get("refreshToken") or "",
            token_expiry=expires_at,
            is_valid=True,
            last_used_at=timezone.now(),
        )
        self._log("fyers.exchange_auth_code", {"client_id": self._client_id()}, {"session_id": session.id, "expires_at": expires_at.isoformat()}, started_at=started_at)
        return session

    def create_session(self):
        session = self._latest_session()
        if session and session.is_valid and session.token_expiry > timezone.now():
            return session
        raise ValueError("No valid Fyers trading session found. Click Connect and complete broker login.")

    def get_profile(self):
        started_at = time.perf_counter()
        response = self._sdk_client().get_profile()
        status_code = 200 if response.get("s") == "ok" else 400
        self._log("fyers.get_profile", {"client_id": self._client_id()}, response, status_code, response.get("message", ""), started_at)
        return response

    def get_funds(self):
        started_at = time.perf_counter()
        response = self._sdk_client().funds()
        status_code = 200 if response.get("s") == "ok" else 400
        self._log("fyers.funds", {"client_id": self._client_id()}, response, status_code, response.get("message", ""), started_at)
        return response

    def get_orderbook(self):
        started_at = time.perf_counter()
        response = self._sdk_client().orderbook()
        status_code = 200 if response.get("s") == "ok" else 400
        self._log("fyers.orderbook", {"client_id": self._client_id()}, response, status_code, response.get("message", ""), started_at)
        return response

    def get_positions(self):
        started_at = time.perf_counter()
        response = self._sdk_client().positions()
        status_code = 200 if response.get("s") == "ok" else 400
        self._log("fyers.positions", {"client_id": self._client_id()}, response, status_code, response.get("message", ""), started_at)
        return response

    def place_order(self, payload):
        started_at = time.perf_counter()
        settings_obj = OrderSettings.objects.filter(user=self.credential.user).first()
        order_type_map = {
            "LIMIT": FyersOrderType.LIMIT,
            "MARKET": FyersOrderType.MARKET,
            "STOP_MARKET": FyersOrderType.STOP_MARKET,
            "STOP_LIMIT": FyersOrderType.STOP_LIMIT,
        }
        # Normalize Side and Type
        side_val = str(payload.get("side", "BUY")).upper()
        type_val = str(payload.get("order_type", "MARKET")).upper()
        limit_price = 0 if type_val in {"MARKET", "STOP_MARKET"} else float(payload.get("price") or 0)
        stop_price = float(payload.get("trigger_price") or 0) if type_val in {"STOP_MARKET", "STOP_LIMIT"} else 0
        
        fyers_payload = {
            "symbol": payload.get("instrument"),
            "qty": int(payload.get("quantity") or 0),
            "type": int(order_type_map.get(type_val, FyersOrderType.MARKET)),
            "side": int(FyersOrderSide.BUY if side_val == "BUY" else FyersOrderSide.SELL),
            "productType": payload.get("product_type") or "INTRADAY",
            "limitPrice": limit_price,
            "stopPrice": stop_price,
            "validity": payload.get("validity") or "DAY",
            "disclosedQty": int(payload.get("disclosed_qty") or 0),
            "offlineOrder": bool(getattr(settings_obj, "use_amo_orders", False)),
            "orderTag": payload.get("order_tag") or payload.get("tag") or "QuantNest",
        }
        response = self._sdk_client().place_order(fyers_payload)
        ok = response.get("s") == "ok" or response.get("code") == 1101
        mapped = {
            "broker_order_id": response.get("id") or response.get("broker_order_id") or "",
            "exchange_order_id": response.get("exchOrdId") or response.get("exchange_order_id") or "",
            "status": OrderStatus.PLACED if ok else OrderStatus.REJECTED,
            "filled_quantity": 0 if ok else 0,
            "avg_fill_price": str(payload.get("price") or payload.get("fallback_price") or 0),
            "raw_response": response,
        }
        self._log("fyers.place_order", fyers_payload, mapped, 200 if ok else 400, response.get("message", ""), started_at)
        return mapped

    def cancel_order(self, broker_order_id):
        started_at = time.perf_counter()
        response = self._sdk_client().cancel_order({"id": broker_order_id})
        ok = response.get("s") == "ok"
        mapped = {
            "broker_order_id": broker_order_id,
            "status": OrderStatus.CANCELLED if ok else OrderStatus.REJECTED,
            "raw_response": response,
        }
        self._log("fyers.cancel_order", {"id": broker_order_id}, mapped, 200 if ok else 400, response.get("message", ""), started_at)
        return mapped


BROKER_ADAPTERS = {
    BrokerName.ZERODHA: ZerodhaAdapter,

    BrokerName.FYERS: FyersAdapter,
}


class BrokerService:
    @staticmethod
    def _to_decimal(value, default=Decimal("0")):
        try:
            if value in (None, "", "null"):
                return Decimal(str(default))
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))

    @staticmethod
    def normalize_funds_payload(payload):
        payload = payload or {}
        rows = payload.get("fund_limit") or payload.get("data") or payload.get("funds") or []
        if isinstance(rows, dict):
            rows = rows.get("fund_limit") or rows.get("summary") or list(rows.values())
        rows = rows if isinstance(rows, list) else []

        summary = {
            "cash_balance": Decimal("0"),
            "available_margin": Decimal("0"),
            "used_margin": Decimal("0"),
            "collateral": Decimal("0"),
            "withdrawable_balance": Decimal("0"),
            "net_equity": Decimal("0"),
            "realized_pnl": Decimal("0"),
            "unrealized_pnl": Decimal("0"),
        }

        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or row.get("id") or row.get("label") or row.get("name") or "").lower()
            amount = BrokerService._to_decimal(
                row.get("equityAmount")
                or row.get("amount")
                or row.get("net")
                or row.get("value")
                or row.get("availablecash")
                or row.get("available_cash")
                or row.get("available")
                or row.get("cash")
            )
            if "available" in title and "margin" in title:
                summary["available_margin"] = max(summary["available_margin"], amount)
            elif "available" in title and ("cash" in title or "balance" in title):
                summary["cash_balance"] = max(summary["cash_balance"], amount)
                summary["available_margin"] = max(summary["available_margin"], amount)
            elif "utilised" in title or "utilized" in title or "used margin" in title:
                summary["used_margin"] = max(summary["used_margin"], amount)
            elif "collateral" in title:
                summary["collateral"] = max(summary["collateral"], amount)
            elif "withdraw" in title:
                summary["withdrawable_balance"] = max(summary["withdrawable_balance"], amount)

        if payload.get("overall") and isinstance(payload["overall"], dict):
            overall = payload["overall"]
            summary["cash_balance"] = BrokerService._to_decimal(overall.get("cash") or overall.get("available_balance"), summary["cash_balance"])
            summary["available_margin"] = BrokerService._to_decimal(overall.get("available_margin") or overall.get("available_cash"), summary["available_margin"])
            summary["used_margin"] = BrokerService._to_decimal(overall.get("used_margin"), summary["used_margin"])
            summary["collateral"] = BrokerService._to_decimal(overall.get("collateral"), summary["collateral"])
            summary["withdrawable_balance"] = BrokerService._to_decimal(overall.get("withdrawable_balance"), summary["withdrawable_balance"])
            summary["net_equity"] = BrokerService._to_decimal(overall.get("net_equity") or overall.get("equity"), summary["net_equity"])

        if payload.get("data") and isinstance(payload["data"], dict):
            data = payload["data"]
            available = data.get("availablecash") or data.get("availableCash") or data.get("available_margin")
            utilized = data.get("utiliseddebits") or data.get("used_margin") or data.get("utilized")
            collateral = data.get("collateral")
            summary["cash_balance"] = BrokerService._to_decimal(available, summary["cash_balance"])
            summary["available_margin"] = BrokerService._to_decimal(available, summary["available_margin"])
            summary["used_margin"] = BrokerService._to_decimal(utilized, summary["used_margin"])
            summary["collateral"] = BrokerService._to_decimal(collateral, summary["collateral"])
            summary["withdrawable_balance"] = BrokerService._to_decimal(data.get("net") or available, summary["withdrawable_balance"])
            summary["net_equity"] = BrokerService._to_decimal(data.get("net") or data.get("equity"), summary["net_equity"])

        if summary["net_equity"] <= 0:
            summary["net_equity"] = summary["cash_balance"] + summary["collateral"] + summary["used_margin"]
        if summary["withdrawable_balance"] <= 0:
            summary["withdrawable_balance"] = summary["cash_balance"]
        if summary["available_margin"] <= 0:
            summary["available_margin"] = summary["cash_balance"]

        return summary

    @staticmethod
    def record_funds_snapshot(credential, payload):
        normalized = BrokerService.normalize_funds_payload(payload)
        snapshot = BrokerFundsSnapshot.objects.create(
            credential=credential,
            cash_balance=normalized["cash_balance"],
            available_margin=normalized["available_margin"],
            used_margin=normalized["used_margin"],
            collateral=normalized["collateral"],
            withdrawable_balance=normalized["withdrawable_balance"],
            net_equity=normalized["net_equity"],
            realized_pnl=normalized["realized_pnl"],
            unrealized_pnl=normalized["unrealized_pnl"],
            raw_payload=BrokerService.as_json_safe(payload),
            snapshot_time=timezone.now(),
        )
        return snapshot

    @staticmethod
    def as_json_safe(value):
        return BaseBrokerAdapter._json_safe(value)

    @staticmethod
    def get_broker_catalog(user):
        credentials = {
            item.broker_name: item
            for item in BrokerCredential.objects.filter(user=user).prefetch_related("sessions")
        }
        catalog = []
        for broker_name, config in BROKER_CATALOG.items():
            credential = credentials.get(broker_name)
            latest_session = None
            latest_session_any = None
            if credential:
                latest_session_any = credential.sessions.order_by("-created_at").first()
                latest_session = credential.sessions.filter(is_valid=True).order_by("-created_at").first()
                if latest_session and latest_session.token_expiry <= timezone.now():
                    latest_session.is_valid = False
                    latest_session.save(update_fields=["is_valid", "updated_at"])
                    latest_session = None
            catalog.append(
                {
                    **config,
                    "configured": credential is not None,
                    "credential_id": credential.id if credential else None,
                    "label": credential.label if credential else config["display_name"],
                    "account_name": (
                        (credential.permissions or {}).get("account_name")
                        if credential
                        else ""
                    ),
                    "account_reference": (
                        (credential.permissions or {}).get("account_reference")
                        if credential
                        else ""
                    ),
                    "is_verified": bool(credential.is_verified) if credential else False,
                    "is_active": bool(credential.is_active) if credential else False,
                    "last_verified_at": (
                        credential.last_verified_at.isoformat()
                        if credential and credential.last_verified_at
                        else None
                    ),
                    "session_valid": bool(latest_session and latest_session.token_expiry > timezone.now()),
                    "session_expired": bool(
                        latest_session_any
                        and latest_session_any.token_expiry
                        and latest_session_any.token_expiry <= timezone.now()
                    ),
                    "session_expires_at": (
                        latest_session.token_expiry.isoformat()
                        if latest_session and latest_session.token_expiry
                        else None
                    ),
                }
            )
        return BrokerService.as_json_safe(catalog)

    @staticmethod
    def get_order_settings(credential):
        settings, _ = OrderSettings.objects.get_or_create(broker_credential=credential)
        return settings

    @staticmethod
    def get_adapter(credential):
        adapter_cls = BROKER_ADAPTERS.get(credential.broker_name, FyersAdapter)
        return adapter_cls(credential)

    @staticmethod
    @transaction.atomic
    def prepare_connection(user, broker_name):
        broker_config = BROKER_CATALOG.get(broker_name)
        if not broker_config or not broker_config.get("enabled"):
            raise ValueError(f"{broker_name} is not enabled yet")

        if broker_name == BrokerName.FYERS:
            client_id = (
                getattr(settings, "BROKER_FYERS_CLIENT_ID", "")
                or getattr(settings, "FYERS_CLIENT_ID", "")
            )
            if not client_id:
                raise BrokerConnectionConfigError(
                    "Set BROKER_FYERS_CLIENT_ID in backend settings before connecting Fyers."
                )
            credential = (
                BrokerCredential.objects.filter(user=user, broker_name=BrokerName.FYERS)
                .order_by("-id")
                .first()
            )
            if credential:
                updates = []
                if credential.client_id != FYERS_PLATFORM_CLIENT_REF:
                    credential.client_id = FYERS_PLATFORM_CLIENT_REF
                    updates.append("client_id")
                if credential.api_key:
                    credential.api_key = ""
                    updates.append("api_key")
                if credential.api_secret:
                    credential.api_secret = ""
                    updates.append("api_secret")
                if credential.totp_secret:
                    credential.totp_secret = ""
                    updates.append("totp_secret")
                if not credential.label:
                    credential.label = "Fyers Account"
                    updates.append("label")
                if updates:
                    credential.save(update_fields=[*updates, "updated_at"])
            else:
                credential = BrokerCredential.objects.create(
                    user=user,
                    broker_name=BrokerName.FYERS,
                    client_id=FYERS_PLATFORM_CLIENT_REF,
                    label="Fyers Account",
                    is_active=False,
                    is_verified=False,
                )
            return {
                "credential": credential,
                "auth_url": BrokerService.generate_auth_url(credential),
            }



        raise ValueError(f"{broker_name} connection flow is not implemented yet")

    @staticmethod
    @transaction.atomic
    def verify_credential(credential):
        result = BrokerService.get_adapter(credential).verify()
        credential.is_verified = bool(result["verified"])
        credential.last_verified_at = timezone.now() if credential.is_verified else None
        profile = result.get("profile") or {}
        profile_data = profile.get("data") if isinstance(profile, dict) else {}
        profile_data = profile_data if isinstance(profile_data, dict) else {}
        account_name = (
            profile_data.get("display_name")
            or profile_data.get("name")
            or profile_data.get("fy_id")
            or credential.label
            or "Fyers Account"
        )
        account_reference = profile_data.get("fy_id") or profile_data.get("email_id") or ""
        credential.label = account_name
        credential.permissions = {
            **(credential.permissions or {}),
            "account_name": account_name,
            "account_reference": account_reference,
            "broker_user_id": profile_data.get("fy_id", ""),
            "email": profile_data.get("email_id", ""),
            "mobile": profile_data.get("mobile_number", ""),
        }
        credential.save(update_fields=["is_verified", "last_verified_at", "label", "permissions", "updated_at"])
        if not credential.is_verified:
            try:
                NotificationService.notify(
                    user=credential.user,
                    title="Broker Verification Failed",
                    message=f"Broker credential '{credential.label}' failed verification. Please re-authenticate.",
                    notification_type=NotificationType.SYSTEM_ALERT,
                    severity=Severity.WARNING,
                    data={"broker_credential_id": str(credential.id), "module": "broker"}
                )
            except Exception:
                logger.exception("Failed dispatching broker verification failure notification")
        return BrokerService.as_json_safe(result)

    @staticmethod
    @transaction.atomic
    def activate_credential(credential):
        if not credential.is_verified:
            raise ValueError("Broker credential must be verified before activation")
        BrokerCredential.objects.filter(user=credential.user).exclude(id=credential.id).update(is_active=False)
        credential.is_active = True
        credential.save(update_fields=["is_active", "updated_at"])
        return credential

    @staticmethod
    @transaction.atomic
    def disconnect_credential(credential):
        credential.sessions.filter(is_valid=True).update(is_valid=False)
        credential.is_active = False
        credential.is_verified = False
        credential.last_verified_at = None
        credential.save(update_fields=["is_active", "is_verified", "last_verified_at", "updated_at"])
        
        # Stop running live strategies associated with this credential
        try:
            from live_trading.models import TradingSession
            from live_trading.services import LiveExecutionService
            active_sessions = TradingSession.objects.filter(broker_credential=credential, status="RUNNING")
            for session in active_sessions:
                LiveExecutionService.stop_session(session, close_positions=False)
        except Exception as e:
            logger.exception(f"Failed to stop live sessions for disconnected credential {credential.id}: {e}")
            
        NotificationService.notify(
            user=credential.user,
            title="Broker Disconnected",
            message=f"Broker connection for '{credential.label}' has been disconnected and all dependent live strategies stopped.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.CRITICAL,
            data={"broker_credential_id": str(credential.id), "module": "broker"}
        )
        return credential

    @staticmethod
    @transaction.atomic
    def ensure_session(credential):
        session = credential.sessions.filter(is_valid=True, token_expiry__gt=timezone.now()).order_by("-created_at").first()
        if session:
            session.last_used_at = timezone.now()
            session.save(update_fields=["last_used_at", "updated_at"])
            return session
        expired_session = credential.sessions.filter(token_expiry__lte=timezone.now()).order_by("-token_expiry").first()
        if expired_session:
            expired_session.is_valid = False
            expired_session.save(update_fields=["is_valid", "updated_at"])
            notify_broker_session_expired(credential)
        return BrokerService.get_adapter(credential).create_session()

    @staticmethod
    def generate_auth_url(credential):
        return BrokerService.get_adapter(credential).generate_auth_url()

    @staticmethod
    @transaction.atomic
    def exchange_auth_code(credential, auth_code):
        adapter = BrokerService.get_adapter(credential)
        session = adapter.exchange_auth_code(auth_code)
        result = BrokerService.verify_credential(credential)
        if not result.get("verified"):
            session.is_valid = False
            session.save(update_fields=["is_valid", "updated_at"])
            adapter._log(
                "fyers.post_exchange_verify",
                {"credential_id": credential.id},
                result,
                400,
                result.get("message") or "Profile verification failed after token exchange",
            )
            raise ValueError(result.get("message") or "Fyers session was created but profile verification failed")
        BrokerCredential.objects.filter(user=credential.user).exclude(id=credential.id).update(is_active=False)
        credential.is_active = True
        credential.save(update_fields=["is_active", "updated_at"])
        return session

    @staticmethod
    def get_profile(credential):
        return BrokerService.as_json_safe(BrokerService.get_adapter(credential).get_profile())

    @staticmethod
    def get_funds(credential):
        return BrokerService.as_json_safe(BrokerService.get_adapter(credential).get_funds())

    @staticmethod
    def get_orderbook(credential):
        return BrokerService.as_json_safe(BrokerService.get_adapter(credential).get_orderbook())

    @staticmethod
    def place_order(credential, payload):
        BrokerService.ensure_session(credential)
        return BrokerService.get_adapter(credential).place_order(payload)

    @staticmethod
    def get_positions(credential):
        BrokerService.ensure_session(credential)
        return BrokerService.as_json_safe(BrokerService.get_adapter(credential).get_positions())

    @staticmethod
    def cancel_order(credential, broker_order_id):
        BrokerService.ensure_session(credential)
        return BrokerService.get_adapter(credential).cancel_order(broker_order_id)
