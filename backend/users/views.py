import logging
import datetime
from io import BytesIO


import qrcode
import qrcode.image.svg
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import generics, status, throttling
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from dj_rest_auth.jwt_auth import set_jwt_cookies
from common.cache_keys import CacheKeys
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import RegisterView, SocialLoginView
from dj_rest_auth.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetView,
)

from .models import APIKey, BackupCode, UserSession
from .serializers import (
    APIKeySerializer,
    CustomRegisterSerializer,
    UserProfileSerializer,
)


logger = logging.getLogger(__name__)

User = get_user_model()

# ──────────────────────────────────────────────
# Throttle for 2FA verification (brute-force prevention)
# ──────────────────────────────────────────────


class TwoFAVerifyThrottle(throttling.AnonRateThrottle):
    rate = "5/min"


# ──────────────────────────────────────────────
# Auth Views
# ──────────────────────────────────────────────


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # In dj-rest-auth, if user is logged in after registration, the user is available on self.user
        user = getattr(self, "user", None)
        if user:
            refresh = response.data.get("refresh")
            if not refresh and hasattr(response, "cookies"):
                from django.conf import settings
                refresh_cookie = response.cookies.get(settings.REST_AUTH.get("JWT_AUTH_REFRESH_COOKIE", "quantnest-refresh"))
                if refresh_cookie:
                    refresh = refresh_cookie.value
            if refresh:
                _record_session(user, request, refresh)
                
        return response


class TwoStepLoginView(LoginView):
    """Login view that checks for 2FA and returns a signed token instead of raw user_id."""
    
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        self.serializer = self.get_serializer(data=request.data)
        self.serializer.is_valid(raise_exception=True)

        user = self.serializer.validated_data.get("user")
        self.user = user

        otp_devices = [d for d in devices_for_user(user) if d.confirmed]

        if otp_devices:
            # Return a signed token instead of raw user_id — expires in 5 minutes
            signed_token = signing.dumps(user.id, salt="2fa-login")
            return Response(
                {
                    "is_2fa_required": True,
                    "detail": "Two-factor authentication is required.",
                    "login_token": signed_token,
                },
                status=status.HTTP_200_OK,
            )

        # No 2FA — proceed with standard login logic from superclass
        response = super().post(request, *args, **kwargs)
        
        # Standard login — record session
        refresh = response.data.get("refresh")
        if not refresh and hasattr(response, "cookies"):
            from django.conf import settings
            refresh_cookie = response.cookies.get(settings.REST_AUTH.get("JWT_AUTH_REFRESH_COOKIE", "quantnest-refresh"))
            if refresh_cookie:
                refresh = refresh_cookie.value
                
        if refresh:
            _record_session(user, request, refresh)

        return response


class CustomPasswordResetView(PasswordResetView):
    """Override PasswordResetView to explicitly allow any access and disable CSRF."""

    authentication_classes = []
    permission_classes = [AllowAny]


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Override PasswordResetConfirmView to explicitly allow any access."""

    authentication_classes = []
    permission_classes = [AllowAny]


class CustomLogoutView(LogoutView):
    """Override LogoutView to permit logout even if current session/token is invalid."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Extract session_id and delete session before calling super()
        try:
            from django.conf import settings
            from django.core.cache import cache
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh_cookie_name = getattr(settings, "REST_AUTH", {}).get("JWT_AUTH_REFRESH_COOKIE", "quantnest-refresh")
            refresh_token = request.COOKIES.get(refresh_cookie_name) or request.data.get("refresh")
            if refresh_token:
                token_obj = RefreshToken(refresh_token, verify=False)
                session_id = token_obj.payload.get("session_id")
                if session_id:
                    UserSession.objects.filter(session_id=session_id).delete()
                    cache.delete(CacheKeys.AUTH_SESSION.format(session_id=session_id))
        except Exception as e:
            logger.error(f"Error deleting session on logout: {e}")
            
        return super().post(request, *args, **kwargs)


class TwoFactorVerifyView(APIView):
    """Verify OTP during login. Uses signed token to prevent user_id enumeration."""

    permission_classes = [AllowAny]
    throttle_classes = [TwoFAVerifyThrottle]

    def post(self, request):
        login_token = request.data.get("login_token")
        otp_token = request.data.get("otp_token")

        if not login_token or not otp_token:
            return Response(
                {"error": "Both login_token and otp_token are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode signed token (expires after 5 minutes)
        try:
            user_id = signing.loads(login_token, salt="2fa-login", max_age=300)
        except signing.BadSignature:
            return Response(
                {"error": "Invalid or expired login token. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device and device.verify_token(otp_token):
            refresh = RefreshToken.for_user(user)
            _record_session(user, request, str(refresh))
            serialized_user = UserProfileSerializer(user).data
            response = Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": serialized_user,
                }
            )
            set_jwt_cookies(response, refresh.access_token, refresh)
            return response

        # Also try backup codes
        if BackupCode.verify_code(user, otp_token):
            refresh = RefreshToken.for_user(user)
            _record_session(user, request, str(refresh))
            serialized_user = UserProfileSerializer(user).data
            response = Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": serialized_user,
                }
            )
            set_jwt_cookies(response, refresh.access_token, refresh)
            return response

        return Response(
            {"error": "Invalid OTP token."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ──────────────────────────────────────────────
# Google Social Login
# ──────────────────────────────────────────────


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173") + "/google-callback"
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                user = getattr(self, "user", None)
                refresh = response.data.get("refresh")
                if user and refresh:
                    _record_session(user, request, refresh)
            return response
        except Exception as e:
            logger.error("Google login error: %s", str(e), exc_info=True)
            return Response(
                {"detail": "Google authentication failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ──────────────────────────────────────────────
# 2FA Setup / Management
# ──────────────────────────────────────────────


class Get2FAStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        remaining_codes = BackupCode.objects.filter(user=request.user, is_used=False).count()
        return Response({
            "is_2fa_enabled": request.user.is_2fa_enabled,
            "backup_codes_remaining": remaining_codes,
        })


class BackupCodesListView(APIView):
    """Return all unused backup codes for the user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        codes = BackupCode.objects.filter(user=request.user, is_used=False)
        # We can't show the raw codes because they are hashed,
        # but for the 'setup' phase they are returned by TOTPVerifyView already.
        # This view is for general management if needed, but since we don't store 
        # plain text, we can't actually 'list' them later.
        # However, for consistency with the 404 fix, we define this.
        return Response({"detail": "Backup codes can only be viewed during setup or regeneration."}, status=status.HTTP_400_BAD_REQUEST)


class TOTPCreateView(APIView):
    """Create and return a new TOTP device for the user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        device = user.totpdevice_set.filter(confirmed=False).first()

        if not device:
            # Delete any old devices for a clean state
            for old_device in devices_for_user(user):
                old_device.delete()
            device = user.totpdevice_set.create(confirmed=False)

        qr_code_url = device.config_url
        image_factory = qrcode.image.svg.SvgImage
        qr_code_image = qrcode.make(qr_code_url, image_factory=image_factory)

        stream = BytesIO()
        qr_code_image.save(stream)

        return Response(
            {"qr_code": stream.getvalue().decode("utf-8"), "secret_key": device.key},
            status=status.HTTP_201_CREATED,
        )


class TOTPVerifyView(APIView):
    """Verify and confirm the TOTP device, then generate backup codes."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        token = request.data.get("token")

        if token is None:
            return Response(
                {"error": "Token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = user.totpdevice_set.filter(confirmed=False).first()
        if device is None:
            return Response(
                {"error": "No unconfirmed device found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if device.verify_token(token):
            device.confirmed = True
            device.save()
            user.is_2fa_enabled = True
            user.save(update_fields=["is_2fa_enabled"])

            # Generate backup codes
            BackupCode.objects.filter(user=user).delete()  # Clear old codes
            code_pairs = BackupCode.generate_codes(count=10)
            for _, code_hash in code_pairs:
                BackupCode.objects.create(user=user, code_hash=code_hash)

            raw_codes = [pair[0] for pair in code_pairs]

            return Response(
                {
                    "success": "2FA has been enabled.",
                    "backup_codes": raw_codes,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Invalid verification code. Please try again."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class TOTPDisableView(APIView):
    """Disable 2FA — requires password verification."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        password = request.data.get("password")

        if not password:
            return Response(
                {"error": "Password is required to disable 2FA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):
            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for device in devices_for_user(user):
            device.delete()

        user.is_2fa_enabled = False
        user.save(update_fields=["is_2fa_enabled"])

        # Clean up backup codes
        BackupCode.objects.filter(user=user).delete()

        return Response(
            {"success": "2FA has been disabled."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────
# 2FA Backup Codes
# ──────────────────────────────────────────────


class BackupCodesRegenerateView(APIView):
    """Regenerate backup codes (replaces all existing ones)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_2fa_enabled:
            return Response(
                {"error": "2FA is not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password")
        if not password or not user.check_password(password):
            return Response(
                {"error": "Password verification required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete old codes and generate new ones
        BackupCode.objects.filter(user=user).delete()
        code_pairs = BackupCode.generate_codes(count=10)
        for _, code_hash in code_pairs:
            BackupCode.objects.create(user=user, code_hash=code_hash)

        raw_codes = [pair[0] for pair in code_pairs]
        return Response({"backup_codes": raw_codes}, status=status.HTTP_200_OK)


class BackupCodesCountView(APIView):
    """Return count of remaining unused backup codes."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = BackupCode.objects.filter(user=request.user, is_used=False).count()
        return Response({"remaining": count})


class BackupCodeVerifyView(APIView):
    """Verify a backup code during 2FA login."""

    permission_classes = [AllowAny]
    throttle_classes = [TwoFAVerifyThrottle]

    def post(self, request):
        login_token = request.data.get("login_token")
        backup_code = request.data.get("backup_code")

        if not login_token or not backup_code:
            return Response(
                {"error": "Both login_token and backup_code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = signing.loads(login_token, salt="2fa-login", max_age=300)
        except signing.BadSignature:
            return Response(
                {"error": "Invalid or expired login token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)

        if BackupCode.verify_code(user, backup_code):
            refresh = RefreshToken.for_user(user)
            serialized_user = UserProfileSerializer(user).data
            response = Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": serialized_user,
                }
            )
            set_jwt_cookies(response, refresh.access_token, refresh)
            return response

        return Response(
            {"error": "Invalid backup code."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ──────────────────────────────────────────────
# User Profile
# ──────────────────────────────────────────────


class UserProfileView(generics.RetrieveUpdateAPIView):
    """API endpoint for retrieving and updating the logged-in user's profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [throttling.UserRateThrottle]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            old_avatar = user.avatar

            response = super().update(request, *args, **kwargs)

            # If a new avatar was uploaded, the serializer handles it.
            # We can optionally delete the old file to save space.
            new_avatar = user.avatar
            if old_avatar and old_avatar != new_avatar:
                try:
                    old_avatar.delete(save=False)
                except Exception as e:
                    logger.warning("Failed to delete old avatar: %s", e)

            return response
        except ValidationError as e:
            logger.warning("Validation error in profile update: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected error in profile update: %s", e)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if not user.avatar:
            return Response(
                {"detail": "No avatar to delete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar"])
            return Response({"detail": "Avatar deleted."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to delete avatar: %s", e)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ──────────────────────────────────────────────
# Subscription & API Keys (Stub APIs — Option A)
# ──────────────────────────────────────────────


class SubscriptionStatusView(APIView):
    """Returns user's subscription status. Stub: always returns Starter plan."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "plan_name": "Starter",
                "is_pro": False,
                "expires_at": None,
                "usage": None,
            }
        )


class APIKeyListCreateView(APIView):
    """List and create API keys."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        serializer = APIKeySerializer(keys, many=True)
        return Response({"keys": serializer.data})

    def post(self, request):
        # Limit to 5 API keys per user
        if APIKey.objects.filter(user=request.user).count() >= 5:
            return Response(
                {"error": "Maximum of 5 API keys allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_key, prefix, key_hash = APIKey.generate_key()
        name = request.data.get("name", "")
        api_key = APIKey.objects.create(
            user=request.user, prefix=prefix, key_hash=key_hash, name=name
        )

        # Return the raw key once (it won't be shown again)
        return Response(
            {
                "id": api_key.id,
                "key": raw_key,
                "prefix": prefix,
                "masked_key": api_key.masked_key,
                "name": name,
                "created_at": api_key.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class APIKeyDeleteView(APIView):
    """Delete a specific API key."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            api_key = APIKey.objects.get(pk=pk, user=request.user)
            api_key.delete()
            return Response(
                {"detail": "API key deleted."},
                status=status.HTTP_200_OK,
            )
        except APIKey.DoesNotExist:
            return Response(
                {"error": "API key not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ──────────────────────────────────────────────
# Account Management
# ──────────────────────────────────────────────

def _graceful_shutdown_user(user):
    """Stop all active trading operations for a user."""
    from paper_trading.models import PaperOrder, PaperAccount
    from brokers.models import BrokerCredential
    from backtesting.models import BacktestRun
    from live_trading.models import LivePortfolio, LiveStrategyAllocation
    from live_trading.services import LiveExecutionService
    from strategy_engine.runtime import StrategyRuntimeState
    
    # 1. Stop all live trading sessions (cancel pending orders, optionally close positions)
    LiveExecutionService.stop_all_sessions(user, close_positions=False)
    
    # 2. Strategy status is no longer used for execution control, so we don't pause them.
    # 3. Cancel all pending paper orders
    PaperOrder.objects.filter(
        account__user=user, 
        status='PENDING'
    ).update(status='CANCELLED')
    
    # 4. Deactivate paper accounts
    PaperAccount.objects.filter(user=user, is_active=True).update(is_active=False)
    
    # 5. Deactivate broker credentials
    BrokerCredential.objects.filter(user=user, is_active=True).update(is_active=False)
    
    # 6. Stop running backtests
    BacktestRun.objects.filter(
        user=user, status__in=['PENDING', 'RUNNING']
    ).update(status='CANCELLED')
    
    # 7. Deactivate live portfolio & strategy allocations
    LivePortfolio.objects.filter(user=user, is_active=True).update(is_active=False)
    LiveStrategyAllocation.objects.filter(user=user, is_active=True).update(is_active=False)
    
    # 8. Clean up Redis runtime state
    StrategyRuntimeState.clear_all_for_user(user.id)


class AccountPreflightView(APIView):
    """Returns a summary of active resources that will be affected."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from strategies.models import Strategy
        from live_trading.models import TradingSession, LivePosition, LiveOrder
        from paper_trading.models import PaperAccount, PaperOrder, PaperPosition
        from brokers.models import BrokerCredential
        from backtesting.models import BacktestRun
        
        return Response({
            "active_strategies": Strategy.objects.filter(user=user, status='ACTIVE').count(),
            "running_live_sessions": TradingSession.objects.filter(user=user, status='RUNNING').count(),
            "open_live_positions": LivePosition.objects.filter(user=user).count(),
            "pending_live_orders": LiveOrder.objects.filter(user=user, status__in=['PENDING', 'PLACED', 'MODIFIED']).count(),
            "active_paper_accounts": PaperAccount.objects.filter(user=user, is_active=True).count(),
            "pending_paper_orders": PaperOrder.objects.filter(account__user=user, status='PENDING').count(),
            "open_paper_positions": PaperPosition.objects.filter(account__user=user).count(),
            "active_broker_connections": BrokerCredential.objects.filter(user=user, is_active=True).count(),
            "running_backtests": BacktestRun.objects.filter(user=user, status__in=['PENDING', 'RUNNING']).count(),
        })


class AccountDeactivateView(APIView):
    """Deactivate user account (set is_active=False)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        _graceful_shutdown_user(user)
        user.is_active = False
        user.save(update_fields=["is_active"])

        # Blacklist all tokens
        _blacklist_all_tokens(user)

        return Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )


class AccountDeleteView(APIView):
    """Permanently delete user account."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        from live_trading.models import LivePosition
        # Block deletion if user has open live positions
        open_live = LivePosition.objects.filter(user=user).exists()
        if open_live:
            return Response(
                {"error": "You have open live positions. Please close all live positions before deleting your account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _graceful_shutdown_user(user)

        # Blacklist all tokens first
        _blacklist_all_tokens(user)

        # Soft delete user (keep data but deactivate and anonymize)
        user.is_active = False
        user.email = f"deleted_{user.id}@example.com"
        user.username = f"deleted_user_{user.id}"
        user.first_name = ""
        user.last_name = ""
        user.bio = ""
        
        # If there's an avatar, we should probably delete the file to save space and remove PII
        if user.avatar:
            user.avatar.delete(save=False)
            
        user.save(update_fields=["is_active", "email", "username", "first_name", "last_name", "bio", "avatar"])

        # Also delete personal specific related objects like BackupCodes and UserSessions
        from users.models import BackupCode, UserSession
        BackupCode.objects.filter(user=user).delete()
        UserSession.objects.filter(user=user).delete()
        
        # Anonymize community content
        from community.models import Post
        Post.objects.filter(author=user).update(is_anonymous=True) if hasattr(Post, 'is_anonymous') else None
        # We leave the author pointing to the soft-deleted anonymized user, so that's actually enough
        # The user's name is "deleted_user_X" so their posts will show up as from "deleted_user_X"

        response = Response(
            {"detail": "Account soft deleted and anonymized."},
            status=status.HTTP_200_OK,
        )
        # Clear the HTTP-only JWT cookies to prevent phantom session errors
        from dj_rest_auth.jwt_auth import unset_jwt_cookies
        unset_jwt_cookies(response)
        return response


# ──────────────────────────────────────────────
# Session Management & Token Rotation
# ──────────────────────────────────────────────

class CustomTokenRefreshView(APIView):
    """
    Intercepts the token refresh to update the UserSession's JTI.
    Wrapped as an APIView to avoid module-level circular import deadlocks in ASGI.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from dj_rest_auth.jwt_auth import get_refresh_view
        from django.conf import settings
        
        RefreshViewClass = get_refresh_view()
        view_instance = RefreshViewClass()
        view_instance.setup(request._request, *args, **kwargs)
        view_instance.request = request
        view_instance.format_kwarg = None
        
        refresh_cookie_name = getattr(settings, "REST_AUTH", {}).get("JWT_AUTH_REFRESH_COOKIE", "quantnest-refresh")
        old_refresh_token = request.COOKIES.get(refresh_cookie_name) or request.data.get("refresh")
        
        if old_refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                old_token_obj = RefreshToken(old_refresh_token, verify=False)
                session_id = old_token_obj.payload.get("session_id")
                if session_id:
                    # Check if session exists and update activity
                    updated = UserSession.objects.filter(session_id=session_id).update(last_activity=timezone.now())
                    if updated == 0:
                        # Session was revoked/deleted!
                        from dj_rest_auth.jwt_auth import unset_jwt_cookies
                        res = Response({"detail": "Session revoked."}, status=status.HTTP_401_UNAUTHORIZED)
                        unset_jwt_cookies(res)
                        return res
            except Exception as e:
                logger.error(f"Error checking session on refresh: {e}")
                
        # Pass the already parsed DRF request to avoid RawPostDataException
        response = view_instance.post(request, *args, **kwargs)
        
        if response.status_code == 200 and old_refresh_token:
            try:
                # If we made it here, the session existed and we already updated last_activity
                # We just need to update the token in the session record just in case.
                from rest_framework_simplejwt.tokens import RefreshToken
                old_token_obj = RefreshToken(old_refresh_token, verify=False)
                session_id = old_token_obj.payload.get("session_id")
                user_id = old_token_obj.payload.get("user_id")
                if session_id and user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        new_refresh_token = response.cookies.get(refresh_cookie_name)
                        token_str = new_refresh_token.value if new_refresh_token else response.data.get("refresh")
                        if token_str:
                            _record_session(user, request, token_str)
            except Exception as e:
                logger.error(f"Error updating UserSession on refresh: {e}")
                
        return response



class ActiveSessionsView(APIView):
    """List user's active sessions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_sessions = UserSession.objects.filter(
            user=request.user, expires_at__gt=timezone.now()
        )

        current_session_id = request.auth.get("session_id") if request.auth else None

        sessions = []
        for session_metadata in active_sessions:
            is_current = (
                str(session_metadata.session_id) == str(current_session_id)
            ) if current_session_id else False
            sessions.append(
                {
                    "id": session_metadata.id,
                    "created_at": session_metadata.created_at.isoformat(),
                    "last_activity": session_metadata.last_activity.isoformat(),
                    "is_current": is_current,
                    "ip_address": session_metadata.ip_address or "N/A",
                    "user_agent": session_metadata.user_agent or "N/A",
                    "browser": session_metadata.browser,
                    "os": session_metadata.os,
                    "device": session_metadata.device_type,
                }
            )

        sessions.sort(key=lambda x: (not x["is_current"], x["last_activity"]), reverse=True)
        return Response({"sessions": sessions})


class RevokeSessionView(APIView):
    """Revoke a specific session."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            from django.core.cache import cache
            session = UserSession.objects.filter(pk=pk, user=request.user).first()
            if session:
                session_id = session.session_id
                session.delete()
                cache.delete(CacheKeys.AUTH_SESSION.format(session_id=session_id))
                return Response({"detail": "Session revoked."}, status=status.HTTP_200_OK)
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error revoking session: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LogoutAllView(APIView):
    """Blacklist all outstanding tokens for the user — logout everywhere."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.conf import settings
        
        exclude_session_id = None
        refresh_cookie_name = getattr(settings, "REST_AUTH", {}).get("JWT_AUTH_REFRESH_COOKIE", "quantnest-refresh")
        refresh_token = request.COOKIES.get(refresh_cookie_name)
        if refresh_token:
            try:
                token_obj = RefreshToken(refresh_token, verify=False)
                exclude_session_id = token_obj.payload.get("session_id")
            except Exception:
                pass
                
        _blacklist_all_tokens(request.user, exclude_session_id=exclude_session_id)
        return Response(
            {"detail": "Logged out from all other devices."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────
# Email Verification Resend
# ──────────────────────────────────────────────


class ResendVerificationEmailView(APIView):
    """Resend the email verification link."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            email_address = EmailAddress.objects.get(email=email)
            if email_address.verified:
                return Response(
                    {"detail": "Email is already verified."},
                    status=status.HTTP_200_OK,
                )
            email_address.send_confirmation(request._request)
            return Response(
                {"detail": "Verification email sent."},
                status=status.HTTP_200_OK,
            )
        except EmailAddress.DoesNotExist:
            # Don't reveal whether the email exists
            return Response(
                {"detail": "If this email is registered, a verification link has been sent."},
                status=status.HTTP_200_OK,
            )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _record_session(user, request, refresh_token):
    """Create a UserSession record from a refresh token and request metadata."""
    try:
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken(refresh_token)
        import uuid
        session_id = token.payload.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            
        exp = token.payload.get("exp")
        expires_at = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc)

        # Basic User Agent parsing
        ua_string = request.META.get("HTTP_USER_AGENT", "")
        browser = "Unknown Browser"
        os = "Unknown OS"
        device = "Desktop"

        if "Mobile" in ua_string:
            device = "Mobile"
        if "Tablet" in ua_string:
            device = "Tablet"

        if "Edg" in ua_string or "Edge" in ua_string:
            browser = "Edge"
        elif "OPR" in ua_string or "Opera" in ua_string:
            browser = "Opera"
        elif "Chrome" in ua_string:
            browser = "Chrome"
        elif "Firefox" in ua_string:
            browser = "Firefox"
        elif "Safari" in ua_string:
            browser = "Safari"

        if "Windows" in ua_string:
            os = "Windows"
        elif "Macintosh" in ua_string:
            os = "macOS"
        elif "Linux" in ua_string:
            os = "Linux"
        elif "Android" in ua_string:
            os = "Android"
        elif "iPhone" in ua_string or "iPad" in ua_string:
            os = "iOS"

        # Get IP address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")

        UserSession.objects.update_or_create(
            session_id=session_id,
            defaults={
                "user": user,
                "ip_address": ip,
                "user_agent": ua_string[:500],
                "browser": browser,
                "os": os,
                "device_type": device,
                "expires_at": expires_at,
            },
        )
    except Exception as e:
        logger.error(f"Error recording session: {e}")


def _blacklist_all_tokens(user, exclude_session_id=None):
    """Blacklist all outstanding refresh tokens for a user and clear sessions."""
    tokens = OutstandingToken.objects.filter(user=user)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)
        
    from django.core.cache import cache
    
    # Also delete all our custom session records
    sessions = UserSession.objects.filter(user=user)
    if exclude_session_id:
        sessions = sessions.exclude(session_id=exclude_session_id)
        
    for session in sessions:
        cache.delete(CacheKeys.AUTH_SESSION.format(session_id=session.session_id))
    sessions.delete()