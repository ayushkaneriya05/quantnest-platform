from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BrokerAPILog, BrokerChargeProfile, BrokerCredential, BrokerSession, OrderReconciliation
from .serializers import (
    BrokerAPILogSerializer,
    BrokerChargeProfileSerializer,
    BrokerCredentialSerializer,
    BrokerFundsSnapshotSerializer,
    BrokerSessionSerializer,
    OrderReconciliationSerializer,
    OrderSettingsSerializer,
)
from .services import BrokerService

import logging

logger = logging.getLogger(__name__)


def broker_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def broker_json_response(payload, status_code=status.HTTP_200_OK):
    return Response(BrokerService.as_json_safe(payload), status=status_code)


class BrokerCredentialViewSet(viewsets.ModelViewSet):
    serializer_class = BrokerCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrokerCredential.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        requested_active = bool(serializer.validated_data.get("is_active"))
        credential = serializer.save(user=self.request.user)
        BrokerService.verify_credential(credential)
        if requested_active and credential.is_verified:
            BrokerService.activate_credential(credential)
        elif credential.is_active and not credential.is_verified:
            credential.is_active = False
            credential.save(update_fields=["is_active", "updated_at"])

    def perform_update(self, serializer):
        requested_active = serializer.validated_data.get(
            "is_active",
            serializer.instance.is_active,
        )
        credential = serializer.save()
        BrokerService.verify_credential(credential)
        if requested_active and credential.is_verified:
            BrokerService.activate_credential(credential)
        elif credential.is_active and not credential.is_verified:
            credential.is_active = False
            credential.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return broker_json_response(BrokerService.verify_credential(self.get_object()))

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            credential = BrokerService.activate_credential(self.get_object())
            return Response(self.get_serializer(credential).data)
        except ValueError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["post"])
    def disconnect(self, request, pk=None):
        credential = BrokerService.disconnect_credential(self.get_object())
        return Response(self.get_serializer(credential).data)

    @action(detail=True, methods=["post"], url_path="create-session")
    def create_session(self, request, pk=None):
        credential = self.get_object()
        auth_code = request.data.get("auth_code")
        try:
            session = (
                BrokerService.exchange_auth_code(credential, auth_code)
                if auth_code
                else BrokerService.ensure_session(credential)
            )
            return broker_json_response(BrokerSessionSerializer(session).data, status.HTTP_201_CREATED)
        except ValueError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["get"], url_path="auth-url")
    def auth_url(self, request, pk=None):
        try:
            return broker_json_response({"auth_url": BrokerService.generate_auth_url(self.get_object())})
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

    @action(detail=True, methods=["post"], url_path="exchange-auth-code")
    def exchange_auth_code(self, request, pk=None):
        try:
            session = BrokerService.exchange_auth_code(self.get_object(), request.data.get("auth_code"))
            return broker_json_response(BrokerSessionSerializer(session).data, status.HTTP_201_CREATED)
        except ValueError as exc:
            return broker_error_response(exc)
        except RuntimeError as exc:
            return broker_error_response(exc)

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

    @action(detail=False, methods=["post"])
    def connect(self, request):
        try:
            result = BrokerService.prepare_connection(
                request.user,
                request.data.get("broker_name"),
            )
            return broker_json_response(
                {
                    "credential": BrokerCredentialSerializer(result["credential"]).data,
                    "auth_url": result.get("auth_url"),
                },
                status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return broker_error_response(exc)


class BrokerSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BrokerSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrokerSession.objects.filter(credential__user=self.request.user).select_related("credential")


class OrderSettingsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        credential_id = request.query_params.get("credential_id")
        if not credential_id:
            return Response({"error": "credential_id is required"}, status=400)
        from brokers.models import BrokerCredential
        credential = BrokerCredential.objects.filter(id=credential_id, user=request.user).first()
        if not credential:
            return Response({"error": "Broker credential not found"}, status=404)
        return Response(OrderSettingsSerializer(BrokerService.get_order_settings(credential)).data)

    def partial_update(self, request, pk=None):
        credential_id = request.data.get("credential_id")
        if not credential_id:
            return Response({"error": "credential_id is required"}, status=400)
        from brokers.models import BrokerCredential
        credential = BrokerCredential.objects.filter(id=credential_id, user=request.user).first()
        if not credential:
            return Response({"error": "Broker credential not found"}, status=404)
        settings_obj = BrokerService.get_order_settings(credential)
        serializer = OrderSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OrderReconciliationViewSet(viewsets.ModelViewSet):
    serializer_class = OrderReconciliationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OrderReconciliation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        item = self.get_object()
        item.resolved = True
        item.resolved_at = timezone.now()
        item.notes = request.data.get("notes", item.notes)
        item.save(update_fields=["resolved", "resolved_at", "notes", "updated_at"])
        return Response(self.get_serializer(item).data)


from rest_framework.pagination import PageNumberPagination

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


@csrf_exempt
def fyers_broker_callback(request):
    auth_code = request.GET.get("auth_code") or request.GET.get("authCode")
    raw_state = request.GET.get("state")
    if not auth_code or not raw_state:
        return HttpResponseBadRequest("Missing auth_code or state")

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    redirect_url = f"{frontend_url}/dashboard/brokers"

    try:
        state_data = signing.loads(raw_state, salt="broker-oauth-state", max_age=900)
        credential = BrokerCredential.objects.get(
            id=state_data.get("credential_id"),
            user_id=state_data.get("user_id"),
            broker_name=state_data.get("broker_name"),
        )
        BrokerService.exchange_auth_code(credential, auth_code)
        return HttpResponseRedirect(
            f"{redirect_url}?{urlencode({'broker': credential.broker_name, 'status': 'connected'})}"
        )
    except Exception as exc:
        logger.exception("Fyers broker callback failed: %s", exc)
        return HttpResponseRedirect(
            f"{redirect_url}?{urlencode({'broker': 'FYERS', 'status': 'failed', 'message': str(exc)})}"
        )


class BrokerChargeProfileViewSet(viewsets.ModelViewSet):
    """CRUD for broker charge profiles with set-default action."""
    serializer_class = BrokerChargeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BrokerChargeProfile.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Set this profile as the user's default, unsetting others."""
        profile = self.get_object()
        # Unset all other defaults for this user
        BrokerChargeProfile.objects.filter(
            user=request.user, is_default=True
        ).exclude(pk=profile.pk).update(is_default=False)
        profile.is_default = True
        profile.save(update_fields=['is_default', 'updated_at'])
        return Response(BrokerChargeProfileSerializer(profile, context={'request': request}).data)
