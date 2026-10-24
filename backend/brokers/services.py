"""Common account, session and ledger operations over registered broker adapters."""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from common.enums import BrokerName, NotificationType
from notifications.services import NotificationService
from .base import BaseBrokerAdapter
from .fyers import FyersAdapter
from .models import BrokerCredential, BrokerFundsSnapshot

logger = logging.getLogger(__name__)

BROKER_CATALOG = {
    BrokerName.FYERS: {
        "broker_name": BrokerName.FYERS,
        "display_name": "Fyers",
        "description": "Connect a Fyers trading account for live order execution and order-status synchronization.",
        "auth_type": "INDIVIDUAL_APP",
        "enabled": True,
        "logo_text": "FY",
    },
    BrokerName.ZERODHA: {
        "broker_name": BrokerName.ZERODHA,
        "display_name": "Zerodha",
        "description": "Live trading integration is planned.",
        "auth_type": "OAUTH_REDIRECT",
        "enabled": False,
        "logo_text": "ZD",
    },
    BrokerName.ANGEL: {
        "broker_name": BrokerName.ANGEL,
        "display_name": "Angel One",
        "description": "Live trading integration is planned.",
        "auth_type": "OAUTH_REDIRECT",
        "enabled": False,
        "logo_text": "AG",
    },
}

BROKER_ADAPTERS = {BrokerName.FYERS: FyersAdapter}

class BrokerService:
    @staticmethod
    def get_profile(credential):
        return BrokerService.get_adapter(credential).get_profile()

    @staticmethod
    def get_funds(credential):
        return BrokerService.get_adapter(credential).get_funds()

    @staticmethod
    def get_orderbook(credential):
        """Adapters return a list of normalized order dictionaries."""
        return BrokerService.get_adapter(credential).get_orderbook()

    @staticmethod
    def place_order(credential, payload, broker_session=None):
        broker_session = broker_session or BrokerService.ensure_session(credential)
        adapter = BrokerService.get_adapter(credential)
        return adapter.place_order(payload, session=broker_session)


    @staticmethod
    def cancel_order(credential, broker_order_id):
        return BrokerService.get_adapter(credential).cancel_order(broker_order_id)


    @staticmethod
    def record_funds_snapshot(credential, funds):
        """Persist the canonical funds shape returned by every broker adapter."""
        return BrokerFundsSnapshot.objects.create(
            credential=credential,
            **{field: funds[field] for field in (
                "cash_balance", "available_margin", "used_margin", "collateral",
                "withdrawable_balance", "net_equity", "realized_pnl", "unrealized_pnl")},
            raw_payload=BrokerService.as_json_safe(funds["raw_payload"]),
            snapshot_time=timezone.now(),
        )

    @staticmethod
    def as_json_safe(value):
        return BaseBrokerAdapter.json_safe(value)

    @staticmethod
    def get_broker_catalog(user):
        credentials = {
            item.broker_name: item
            for item in BrokerCredential.objects.filter(user=user).prefetch_related("sessions").order_by("updated_at", "pk")
        }
        catalog = []
        now = timezone.now()
        for broker_name, config in BROKER_CATALOG.items():
            credential = credentials.get(broker_name)
            latest_session = None
            latest_session_any = None
            if credential:
                sessions = credential.sessions.all()
                latest_session_any = next(iter(sessions), None)
                latest_session = next((session for session in sessions if session.is_valid), None)
                if latest_session and latest_session.token_expiry <= now:
                    latest_session.is_valid = False
                    latest_session.save(update_fields=["is_valid", "updated_at"])
                    latest_session = None
            catalog.append(
                {
                    **config,
                    "configured": bool(credential and credential.client_id and credential.api_secret),
                    "client_id": credential.client_id if credential else "",
                    "connection": BROKER_ADAPTERS[broker_name].connection_details() if broker_name in BROKER_ADAPTERS else {},
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
                    "session_valid": bool(latest_session and latest_session.token_expiry > now),
                    "session_expired": bool(
                        latest_session_any
                        and latest_session_any.token_expiry
                        and latest_session_any.token_expiry <= now
                    ),
                    "session_expires_at": (
                        latest_session.token_expiry.isoformat()
                        if latest_session and latest_session.token_expiry
                        else None
                    ),
                }
            )
        return catalog


    @staticmethod
    def get_adapter(credential):
        adapter_cls = BROKER_ADAPTERS.get(credential.broker_name)
        if adapter_cls is None:
            raise ValueError(f"Broker '{credential.broker_name}' is not supported")
        return adapter_cls(credential)

    @staticmethod
    @transaction.atomic
    def configure_connection(user, broker_name: str, client_id: str, api_secret: str):
        """Save the owner's app. Only a changed app/secret invalidates its token."""
        adapter_class = BROKER_ADAPTERS[broker_name]
        get_user_model().objects.select_for_update().get(pk=user.pk)
        credential = BrokerCredential.objects.select_for_update().filter(user=user, broker_name=broker_name).first()
        if credential is None:
            if not api_secret:
                raise ValueError("Enter the App Secret for your individual broker app.")
            return BrokerCredential.objects.create(
                user=user, broker_name=broker_name, client_id=client_id, api_secret=api_secret,
                label=f"{adapter_class.display_name} Account", is_active=False, is_verified=False,
            )
        changed_app = credential.client_id != client_id
        if changed_app and not api_secret:
            raise ValueError("Enter the App Secret belonging to the new App ID.")
        changed = changed_app or (bool(api_secret) and credential.api_secret != api_secret)
        if changed:
            if credential.client_id:
                from execution.order_reports import TERMINAL
                busy = (
                    credential.live_sessions.filter(status__in=["RUNNING", "STOPPING"]).exists()
                    or credential.live_positions.filter(quantity__gt=0).exists()
                    or credential.live_orders.exclude(status__in=TERMINAL).exists()
                )
                if busy:
                    raise ValueError("Stop live sessions, close positions and reconcile pending orders before changing app credentials.")
            credential.sessions.filter(is_valid=True).update(is_valid=False)
            credential.client_id = client_id
            credential.api_secret = api_secret
            credential.is_active = credential.is_verified = False
            credential.last_verified_at = None
            credential._audit_sensitive_fields = ("client_id", "api_secret")
            credential.save(update_fields=["client_id", "api_secret", "is_active", "is_verified", "last_verified_at", "updated_at"])
        if not credential.api_secret:
            raise ValueError("Enter the App Secret for your individual broker app.")
        return credential

    @staticmethod
    @transaction.atomic
    def verify_credential(credential):
        result = BrokerService.get_adapter(credential).verify()
        credential.is_verified = result["verified"]
        credential.last_verified_at = timezone.now() if credential.is_verified else None
        if credential.is_verified:
            profile = result["profile"]
            previous_account = credential.permissions.get("account_reference")
            if previous_account and previous_account != profile["account_reference"]:
                raise ValueError(f"Sign in with the {credential.broker_name} account already linked to this connection.")
            credential.label = profile["name"]
            credential.permissions = {
                "account_name": profile["name"], "account_reference": profile["account_reference"],
                "email": profile["email"], "mobile": profile["mobile"],
            }
        credential.save(update_fields=["is_verified", "last_verified_at", "label", "permissions", "updated_at"])
        if not credential.is_verified:
            NotificationService.notify(
                user=credential.user, type=NotificationType.WARNING,
                title=f"Broker verification failed: {credential.broker_name}",
                message=result["message"],
                data={"broker_credential_id": str(credential.pk), "module": "broker"},
                dedupe_key=f"broker-verification-failed:{credential.pk}",
            )
        return result

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
            message=f"Broker account '{credential.label or credential.client_id}' disconnected. Dependent live sessions were stopped.",
            type=NotificationType.WARNING,
            title=f"Broker disconnected: {credential.broker_name}",
            data={"broker_credential_id": str(credential.id), "broker_name": credential.broker_name, "module": "broker"},
            dedupe_key=f"broker-disconnected:{credential.id}:{credential.updated_at.isoformat()}"
        )
        return credential

    @staticmethod
    def ensure_session(credential):
        return BrokerService.get_adapter(credential).get_session()

    @staticmethod
    def create_order_stream(credential):
        return BrokerService.get_adapter(credential).create_order_stream()


    @staticmethod
    def generate_auth_url(credential, state: str):
        return BrokerService.get_adapter(credential).generate_auth_url(state)

    @staticmethod
    @transaction.atomic
    def exchange_auth_code(credential, auth_code):
        adapter = BrokerService.get_adapter(credential)
        session = adapter.exchange_auth_code(auth_code)
        result = BrokerService.verify_credential(credential)
        if not result["verified"]:
            session.is_valid = False
            session.save(update_fields=["is_valid", "updated_at"])
            raise ValueError(result["message"])
        BrokerCredential.objects.filter(user=credential.user).exclude(id=credential.id).update(is_active=False)
        credential.is_active = True
        credential.save(update_fields=["is_active", "updated_at"])
        NotificationService.notify(
            user=credential.user,
            type=NotificationType.INFO,
            title=f"Broker connected: {credential.broker_name}",
            message=f"{credential.label or credential.client_id} authenticated successfully and is ready for live trading.",
            data={"broker_credential_id": str(credential.id), "broker_name": credential.broker_name, "module": "broker"},
            dedupe_key=f"broker-connected:{credential.id}:{session.pk}",
        )
        return session
