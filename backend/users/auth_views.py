"""Authentication endpoints use the same login, rotation and revocation services."""
import uuid

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from dj_rest_auth.app_settings import api_settings as auth_settings
from dj_rest_auth.jwt_auth import unset_jwt_cookies
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from rest_framework import throttling
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from .authentication import SafeJWTAuthentication
from .models import BackupCode, UserSession
from .serializers import CustomRegisterSerializer
from .sessions import issue_login_response, refresh_session, refresh_session_connections, revoke_sessions, token_session_id
from .tokens import CustomRefreshToken


class AuthActionMixin:
    """Login and refresh are cookie actions too, so protect them against CSRF."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        SafeJWTAuthentication().enforce_csrf(request)

    def get_authenticate_header(self, request):
        return "Bearer"


class LoginThrottle(throttling.AnonRateThrottle):
    scope = "auth_login"
    rate = "10/min"


class TwoFAVerifyThrottle(throttling.AnonRateThrottle):
    scope = "auth_2fa"
    rate = "5/min"


class SecurityActionThrottle(throttling.UserRateThrottle):
    scope = "auth_security"
    rate = "5/min"


class CSRFTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        response = Response({
            "csrf_token": get_token(request),
            "has_refresh_cookie": bool(request.COOKIES.get(auth_settings.JWT_AUTH_REFRESH_COOKIE)),
        })
        response["Cache-Control"] = "no-store"
        return response


def _challenge_response(user):
    nonce = uuid.uuid4().hex
    cache.set(f"login_challenge_{nonce}", True, timeout=300)
    payload = {"user_id": user.pk, "nonce": nonce, "password_hash": get_md5_hash_password(user.password)}
    return Response({
        "is_2fa_required": True, "message": "Two-factor authentication is required.",
        "login_token": signing.dumps(payload, salt="2fa-login"),
    })


class SessionLoginMixin(AuthActionMixin):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return login_response(serializer.validated_data["user"], request)


def login_response(user, request):
    """Password and Google logins pass the same account and two-factor checks."""
    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return _challenge_response(user)
    return issue_login_response(user, request)


class TwoStepLoginView(SessionLoginMixin, LoginView):
    pass


class CustomRegisterView(AuthActionMixin, RegisterView):
    authentication_classes = []
    serializer_class = CustomRegisterSerializer
    throttle_classes = [LoginThrottle]

    def perform_create(self, serializer):
        self.registered_user = super().perform_create(serializer)
        return self.registered_user

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if getattr(self, "refresh_token", None) is not None:
            return issue_login_response(self.registered_user, request, refresh=self.refresh_token, status=201)
        return response


class TwoFactorVerifyView(AuthActionMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [TwoFAVerifyThrottle]
    code_field = "otp_token"

    @transaction.atomic
    def post(self, request):
        code = request.data.get(self.code_field)
        try:
            challenge = signing.loads(request.data.get("login_token", ""), salt="2fa-login", max_age=300)
        except (signing.BadSignature, TypeError):
            raise ValidationError("Invalid or expired login challenge. Please sign in again.")
        if not isinstance(challenge, dict) or not code:
            raise ValidationError("A login challenge and verification code are required.")
        user = get_user_model().objects.select_for_update().filter(pk=challenge.get("user_id"), is_active=True).first()
        challenge_key = f"login_challenge_{challenge.get('nonce')}"
        if user is None or not cache.get(challenge_key) or challenge.get("password_hash") != get_md5_hash_password(user.password):
            raise ValidationError("Invalid or expired login challenge. Please sign in again.")
        device = TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True).first()
        if device is None:
            raise ValidationError("Two-factor settings have changed. Please sign in again.")
        verified = self.code_field == "otp_token" and device is not None and device.verify_token(code)
        if not verified and not BackupCode.verify_code(user, str(code)):
            raise ValidationError({self.code_field: "Invalid verification code."})
        cache.delete(challenge_key)
        return issue_login_response(user, request)


class BackupCodeVerifyView(TwoFactorVerifyView):
    code_field = "backup_code"


class CustomTokenRefreshView(AuthActionMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(auth_settings.JWT_AUTH_REFRESH_COOKIE)
        if not token:
            raise AuthenticationFailed("Please sign in to continue.")
        try:
            return refresh_session(request, token)
        except TokenError:
            raise AuthenticationFailed("Your session has ended. Please sign in again.")


class CustomLogoutView(AuthActionMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        token = request.COOKIES.get(auth_settings.JWT_AUTH_REFRESH_COOKIE)
        if token:
            try:
                refresh = CustomRefreshToken(token)
                user = get_user_model().objects.select_for_update().filter(pk=refresh.get("user_id")).first()
                # A valid logout can start just before a concurrent token rotation.
                # End that owned session even if its refresh JTI changed meanwhile.
                session = UserSession.objects.filter(user=user, session_id=token_session_id(refresh)).first()
                if session:
                    revoke_sessions(user, session_pk=session.pk)
            except (TokenError, AuthenticationFailed):
                pass  # Already expired or revoked: logout remains idempotent.
        response = Response({"message": "Signed out successfully."})
        unset_jwt_cookies(response)
        return response


class CustomPasswordResetView(AuthActionMixin, PasswordResetView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]


class CustomPasswordResetConfirmView(AuthActionMixin, PasswordResetConfirmView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        get_user_model().objects.select_for_update().get(pk=serializer.user.pk)
        # Revalidate after acquiring the user lock: a reset token is single use.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        revoke_sessions(serializer.user)
        response = Response({"message": "Password reset. Please sign in with your new password."})
        unset_jwt_cookies(response)
        return response


class CustomPasswordChangeView(PasswordChangeView):
    throttle_classes = [SecurityActionThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if request.auth.get(jwt_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed("Your password has changed. Please sign in again.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        revoke_sessions(request.user, exclude_session_id=request.auth["session_id"])
        response = issue_login_response(request.user, request)
        refresh_session_connections(request.auth["session_id"])
        response.data["message"] = "Password changed. Other sessions have been ended."
        return response


class ActiveSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        UserSession.objects.filter(user=request.user, expires_at__lte=timezone.now()).delete()
        sessions = [{
            "id": session.pk, "created_at": session.created_at,
            "expires_at": session.expires_at, "last_activity": session.last_activity,
            "is_current": str(session.session_id) == str(request.auth["session_id"]),
            "ip_address": session.ip_address, "user_agent": session.user_agent,
            "browser": session.browser, "os": session.os, "device": session.device_type,
        } for session in UserSession.objects.filter(user=request.user)]
        sessions.sort(key=lambda session: (not session["is_current"], -session["last_activity"].timestamp()))
        return Response({"sessions": sessions})


class RevokeSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not revoke_sessions(request.user, session_pk=pk):
            raise NotFound("Session not found.")
        return Response({"message": "Session ended."})


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = revoke_sessions(request.user, exclude_session_id=request.auth["session_id"])
        return Response({"message": "All other sessions have been ended.", "revoked_count": count})
