import hmac
import logging
import secrets
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.core import signing
from django.core.cache import cache
from django.utils.crypto import salted_hmac
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_GET
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from common.enums import NotificationType
from notifications.services import NotificationService

from .models import BrokerAPILog, BrokerChargeProfile, BrokerCredential, BrokerSession
from .serializers import (
    BrokerAPILogSerializer,
    BrokerChargeProfileSerializer,
    BrokerCredentialSerializer,
    BrokerConfigurationSerializer,
    BrokerFundsSnapshotSerializer,
    BrokerSessionSerializer,
)
from .services import BrokerService

logger = logging.getLogger(__name__)


def notify_broker_auth_failure(credential, reason):
    if credential is None:
        return
    NotificationService.notify(
        user=credential.user,
        type=NotificationType.WARNING,
        title=f"Broker authentication failed: {credential.broker_name}",
        message=f"{credential.label or credential.client_id}: {reason}",
        data={
            "broker_credential_id": str(credential.id),
            "broker_name": credential.broker_name,
            "module": "broker",
        },
    )


def broker_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def broker_json_response(payload, status_code=status.HTTP_200_OK):
    return Response(BrokerService.as_json_safe(payload), status=status_code)


OAUTH_COOKIE = "quantnest-broker-oauth"
OAUTH_SECONDS = 900


def _connection_version(credential):
    return salted_hmac("broker-app-version", f"{credential.client_id}:{credential.api_secret}").hexdigest()


def _oauth_response(response, *, clear_cookie=False):
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    if clear_cookie:
        response.delete_cookie(OAUTH_COOKIE, path="/api/v1/brokers/", samesite="Lax")
    return response


class BrokerCredentialViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrokerCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrokerCredential.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"])
    def configure(self, request):
        serializer = BrokerConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            credential = BrokerService.configure_connection(
                request.user, serializer.validated_data["broker_name"],
                serializer.validated_data["client_id"], serializer.validated_data.get("api_secret", ""),
            )
        except ValueError as exc:
            return _oauth_response(broker_error_response(exc))
        return broker_json_response(self.get_serializer(credential).data)

    @action(detail=True, methods=["post"])
    def disconnect(self, request, pk=None):
        credential = BrokerService.disconnect_credential(self.get_object())
        return Response(self.get_serializer(credential).data)

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        try:
            return broker_json_response(BrokerService.get_profile(self.get_object()))
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["get"])
    def funds(self, request, pk=None):
        try:
            return broker_json_response(BrokerService.get_funds(self.get_object()))
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["get"], url_path="funds-summary")
    def funds_summary(self, request, pk=None):
        try:
            credential = self.get_object()
            payload = BrokerService.get_funds(credential)
            snapshot = BrokerService.record_funds_snapshot(credential, payload)
            return broker_json_response(BrokerFundsSnapshotSerializer(snapshot).data)
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["get"])
    def orderbook(self, request, pk=None):
        try:
            return broker_json_response(BrokerService.get_orderbook(self.get_object()))
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

    @action(detail=False, methods=["get"])
    def active(self, request):
        credential = self.get_queryset().filter(is_active=True).first()
        if not credential:
            return broker_json_response({})
        return broker_json_response(self.get_serializer(credential).data)

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        return broker_json_response(BrokerService.get_broker_catalog(request.user))

    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None):
        credential = self.get_object()
        try:
            details = BrokerService.get_adapter(credential).connection_details()
            state = signing.dumps({
                "credential_id": credential.pk, "user_id": request.user.pk,
                "nonce": secrets.token_urlsafe(24), "version": _connection_version(credential),
            }, salt="broker-oauth-state")
            response = broker_json_response({"auth_url": BrokerService.generate_auth_url(credential, state)})
            response.set_cookie(
                OAUTH_COOKIE, state, max_age=OAUTH_SECONDS,
                secure=urlsplit(details["redirect_uri"]).scheme == "https",
                httponly=True, samesite="Lax", path="/api/v1/brokers/",
            )
            return _oauth_response(response)
        except ValueError as exc:
            return broker_error_response(exc)


class BrokerSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrokerSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrokerSession.objects.filter(credential__user=self.request.user).select_related("credential")




class BrokerAPILogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500

class BrokerAPILogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrokerAPILogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BrokerAPILogPagination

    def get_queryset(self):
        queryset = BrokerAPILog.objects.filter(credential__user=self.request.user).select_related("credential")

        status_code = self.request.query_params.get("status_code")
        if status_code:
            queryset = queryset.filter(status_code=status_code)

        endpoint = self.request.query_params.get("endpoint")
        if endpoint:
            queryset = queryset.filter(endpoint__icontains=endpoint)

        broker = self.request.query_params.get("broker")
        if broker:
            queryset = queryset.filter(credential__broker_name=broker)

        return queryset.order_by("-created_at")


@require_GET
def fyers_broker_callback(request):
    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/brokers"
    credential = None
    try:
        state = request.GET.get("state", "")
        cookie = request.COOKIES.get(OAUTH_COOKIE, "")
        if not state or not cookie or not hmac.compare_digest(state.encode(), cookie.encode()):
            raise ValueError("Sign-in verification is missing. Start Connect again on the configured hostname in the same browser.")
        payload = signing.loads(state, salt="broker-oauth-state", max_age=OAUTH_SECONDS)
        with transaction.atomic():
            credential = BrokerCredential.objects.select_for_update().select_related("user").get(
                pk=payload["credential_id"], user_id=payload["user_id"], broker_name="FYERS", user__is_active=True,
            )
            if not hmac.compare_digest(payload["version"], _connection_version(credential)):
                raise ValueError("The saved app credentials changed. Start Connect again.")
            if not cache.add("broker-oauth-used:" + payload["nonce"], True, timeout=OAUTH_SECONDS):
                raise ValueError("This sign-in has already been used. Start Connect again.")
            auth_code = request.GET.get("auth_code")
            if not auth_code:
                raise ValueError("FYERS sign-in did not return an authorization code. Start Connect again.")
            BrokerService.exchange_auth_code(credential, auth_code)
        params = {"broker": "FYERS", "status": "connected"}
    except Exception as exc:
        logger.warning("FYERS broker authorization failed credential=%s error=%s",
                       credential.pk if credential else None, type(exc).__name__)
        message = str(exc) if isinstance(exc, ValueError) else "Broker sign-in could not complete. Start Connect again."
        try:
            notify_broker_auth_failure(credential, message)
        except Exception:
            logger.exception("Could not record broker authorization failure")
        params = {"broker": "FYERS", "status": "failed", "message": message}
    return _oauth_response(HttpResponseRedirect(f"{redirect_url}?{urlencode(params)}"), clear_cookie=True)


class BrokerChargeProfileViewSet(viewsets.ModelViewSet):
    """User-owned simulation charge profiles with a set-default action."""
    serializer_class = BrokerChargeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BrokerChargeProfile.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError({'detail': exc.args[0]}) from exc

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Set this profile as the user's default, unsetting others."""
        profile = self.get_object()
        profile.set_default()
        return Response(self.get_serializer(profile).data)
