import hashlib
import hmac
import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from core.request_views import ObjectAPIView as APIView
from commercial.usage import reject_request
from .models import Installation, LocalLicenseState, SupportAuthorization
from .licensing import issue_installation_licence, import_installation_licence, get_local_entitlements
from .signing import verify_licence


class RefreshLicenseView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        if settings.QUANTNEST_DEPLOYMENT_MODE == "private":
            reject_request("licensing_authority_required", "Refresh this installation through the configured QuantNest licensing service.")
        try:
            identity = uuid.UUID(str(request.data.get("installation_id", "")))
        except (ValueError, TypeError):
            reject_request("invalid_installation", "Provide a valid installation identifier.")
        installation = get_object_or_404(Installation.objects.select_related("contract"), pk=identity)
        raw = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not raw or not hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), installation.activation_hash):
            reject_request("invalid_activation", "Installation activation credentials are invalid.")
        return Response({"licence": issue_installation_licence(installation), "refresh_seconds": 21600}, headers={"Cache-Control": "no-store"})


class LocalLicenseView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if settings.QUANTNEST_DEPLOYMENT_MODE != "private":
            reject_request("private_installation_required", "Local installation licences apply only to Private deployments.")
        return Response(get_local_entitlements())
    def post(self, request):
        if settings.QUANTNEST_DEPLOYMENT_MODE != "private":
            reject_request("private_installation_required", "Local installation licences apply only to Private deployments.")
        if not request.user.is_staff:
            reject_request("installation_admin_required", "Only an installation administrator can import a signed licence.")
        try:
            import_installation_licence(request.data.get("licence", ""))
        except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
            reject_request("licence_invalid", "The licence could not be verified. Request a signed licence for this installation.")
        return Response(get_local_entitlements())


class ResumeLicenseView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if settings.QUANTNEST_DEPLOYMENT_MODE != "private":
            reject_request("private_installation_required", "Local installation licences apply only to Private deployments.")
        if not request.user.is_staff:
            reject_request("installation_admin_required", "An installation administrator must enable new work.")
        row = get_object_or_404(LocalLicenseState, installation_id=settings.LICENSE_INSTALLATION_ID)
        try:
            claims = verify_licence(row.token, settings.LICENSE_INSTALLATION_ID)
        except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
            reject_request("licence_invalid", "Import a valid signed licence before enabling new work.")
        if timezone.now().timestamp() >= min(claims["exp"], claims["paid_through"]):
            reject_request("licence_expired", "Refresh the signed licence before enabling new work.")
        row.resume_required = False
        row.save(update_fields=["resume_required"])
        return Response(get_local_entitlements())


class SupportAccessView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        installations = list(Installation.objects.filter(contract__customer=request.user, enabled=True)
                             .order_by("-created_at", "-pk").values("id", "contract__reference"))
        return Response({"authorizations": list(SupportAuthorization.objects.filter(installation_id__in=[row["id"] for row in installations]).order_by("-pk").values(
            "id", "installation_id", "staff_id", "scope", "valid_until", "revoked_at")[:100]),
            "installations": installations,
            "staff": list(get_user_model().objects.filter(is_staff=True, is_active=True).order_by("first_name", "last_name", "pk").values("id", "first_name", "last_name")[:50]) if installations else []})
    def post(self, request):
        try:
            identity = uuid.UUID(str(request.data.get("installation_id", "")))
        except ValueError:
            reject_request("installation_required", "Choose an owned installation.")
        if type(request.data.get("staff_id")) is not int:
            reject_request("support_staff_required", "Choose a named support member.")
        installation = get_object_or_404(Installation, pk=identity, contract__customer=request.user, enabled=True)
        staff = get_object_or_404(get_user_model(), pk=request.data.get("staff_id"), is_staff=True, is_active=True)
        if request.data.get("scope") != "diagnostics" or request.data.get("approved") is not True:
            reject_request("support_scope_required", "Explicitly approve a two-hour diagnostics-only support window.")
        row = SupportAuthorization.objects.create(installation=installation, staff=staff, authorized_by=request.user,
            scope="diagnostics", valid_until=timezone.now()+timedelta(hours=2))
        return Response({"id": row.pk, "valid_until": row.valid_until}, status=201)
    def delete(self, request):
        if type(request.data.get("id")) is not int or request.data["id"] < 1:
            reject_request("authorization_required", "Choose a valid support authorization to revoke.")
        row = get_object_or_404(SupportAuthorization, pk=request.data.get("id"), installation__contract__customer=request.user)
        SupportAuthorization.objects.filter(pk=row.pk, revoked_at__isnull=True).update(revoked_at=timezone.now())
        return Response({"revoked": True})


class SupportDiagnosticsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if not request.user.is_staff:
            reject_request("support_staff_required", "This diagnostic scope is limited to the named support member.")
        row = get_object_or_404(SupportAuthorization.objects.select_related("installation__contract"), pk=pk, staff=request.user, scope="diagnostics",
            revoked_at__isnull=True, valid_until__gt=timezone.now(), installation__enabled=True)
        # Central access shares only contract/refresh metadata. Trading records and
        # customer host credentials are never available through this endpoint.
        return Response({"installation_id": row.installation_id, "last_refresh": row.installation.last_refresh,
            "approved_release": row.installation.contract.supported_releases, "entitlement_revision": row.installation.contract.revision,
            "scope": row.scope, "expires_at": row.valid_until, "server_release": settings.QUANTNEST_RELEASE})
