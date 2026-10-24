"""Broker-neutral adapter contract, session lifecycle and API logging."""
import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone

from common.enums import NotificationType
from notifications.services import NotificationService
from .models import BrokerAPILog


BROKER_SESSION_EXPIRED_CACHE_KEY = "broker_session_expired_notification_{credential_id}"


def notify_broker_session_expired(credential):
    cache_key = BROKER_SESSION_EXPIRED_CACHE_KEY.format(credential_id=credential.pk)
    if cache.get(cache_key):
        return
    NotificationService.notify(
        user=credential.user,
        message=f"Reconnect {credential.label} to continue live trading.",
        type=NotificationType.CRITICAL,
        title=f"{credential.broker_name} session expired: {credential.label}",
        data={"broker_credential_id": str(credential.pk), "broker_name": credential.broker_name, "module": "broker"},
        dedupe_key=f"broker-session-expired:{credential.pk}",
    )
    cache.set(cache_key, True, 3600)


class BaseBrokerAdapter(ABC):
    """Implement vendor payloads in a subclass; return QuantNest dictionaries."""
    broker_name: str
    display_name: str
    configuration_serializer: type

    def __init__(self, credential):
        self.credential = credential

    @staticmethod
    def json_safe(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: BaseBrokerAdapter.json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [BaseBrokerAdapter.json_safe(item) for item in value]
        return value

    def _log(self, endpoint, request_data, response_data, *, started_at, status_code=200, error_message=""):
        BrokerAPILog.objects.create(
            credential=self.credential, endpoint=endpoint,
            request_data=self.json_safe(request_data), response_data=self.json_safe(response_data),
            latency_ms=max(int((time.perf_counter() - started_at) * 1000), 0),
            status_code=status_code, error_message=error_message,
        )

    def get_session(self):
        session = self.credential.sessions.filter(is_valid=True).order_by("-created_at").first()
        if session and session.token_expiry > timezone.now():
            session.last_used_at = timezone.now()
            session.save(update_fields=["last_used_at", "updated_at"])
            return session
        if session:
            session.is_valid = False
            session.save(update_fields=["is_valid", "updated_at"])
            notify_broker_session_expired(self.credential)
        raise ValueError("Reconnect this broker account before using live trading.")

    def verify(self):
        try:
            profile = self.get_profile()
        except ValueError as exc:
            return {"verified": False, "broker": self.broker_name, "message": str(exc), "profile": {}}
        return {"verified": True, "broker": self.broker_name, "message": "Broker account verified.", "profile": profile}

    @staticmethod
    def validate_order(payload: dict):
        if payload["order_type"] != "MARKET":
            raise ValueError("Only MARKET orders are supported for live execution.")
        if payload["side"] not in {"BUY", "SELL"} or payload["quantity"] <= 0:
            raise ValueError("A broker order requires BUY/SELL and a positive quantity.")

    @abstractmethod
    def generate_auth_url(self, state: str) -> str: ...

    @staticmethod
    @abstractmethod
    def connection_details() -> dict: ...

    @abstractmethod
    def exchange_auth_code(self, auth_code: str): ...

    @abstractmethod
    def get_profile(self) -> dict: ...

    @abstractmethod
    def get_funds(self) -> dict: ...

    @abstractmethod
    def get_orderbook(self) -> list[dict]: ...

    @abstractmethod
    def place_order(self, payload: dict, session) -> dict: ...

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> dict: ...

    @abstractmethod
    def create_order_stream(self): ...
