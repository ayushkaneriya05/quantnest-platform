import logging
from io import BytesIO


import qrcode
import qrcode.image.svg
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django_otp import devices_for_user
from rest_framework import generics, status, throttling
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_rest_auth.jwt_auth import unset_jwt_cookies
from django.db import transaction

from .models import BackupCode
from .serializers import UserProfileSerializer
from .sessions import revoke_sessions
from .auth_views import AuthActionMixin, LoginThrottle, SecurityActionThrottle


logger = logging.getLogger(__name__)

User = get_user_model()


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
    """Only counts are retained; plaintext recovery codes are shown once."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"remaining": BackupCode.objects.filter(user=request.user, is_used=False).count()})


class TOTPCreateView(APIView):
    """Create and return a new TOTP device for the user."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        User.objects.select_for_update().get(pk=user.pk)
        if user.totpdevice_set.filter(confirmed=True).exists():
            raise ValidationError("Two-factor authentication is already enabled.")
        device = user.totpdevice_set.filter(confirmed=False).first()

        if not device:
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
    throttle_classes = [SecurityActionThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        User.objects.select_for_update().get(pk=user.pk)
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
            revoke_sessions(user, exclude_session_id=request.auth["session_id"])

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
    throttle_classes = [SecurityActionThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        User.objects.select_for_update().get(pk=user.pk)
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
        revoke_sessions(user, exclude_session_id=request.auth["session_id"])

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
    throttle_classes = [SecurityActionThrottle]

    @transaction.atomic
    def post(self, request):
        user = request.user
        User.objects.select_for_update().get(pk=user.pk)
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
        user = self.get_object()
        old_avatar = user.avatar
        response = super().update(request, *args, **kwargs)
        if old_avatar and old_avatar != user.avatar:
            try:
                transaction.on_commit(lambda: old_avatar.storage.delete(old_avatar.name))
            except OSError:
                logger.exception("Failed to delete replaced avatar")
        return response


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
# Subscription
# ──────────────────────────────────────────────




# ──────────────────────────────────────────────
# Account Management
# ──────────────────────────────────────────────

class AccountPreflightView(APIView):
    """Returns a summary of active resources that will be affected."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from strategies.models import Strategy
        from live_trading.models import TradingSession
        from paper_trading.models import PaperAccount
        from brokers.models import BrokerCredential
        from backtesting.models import BacktestRun
        from .privacy import get_account_exposure
        from commercial.models import Subscription
        exposure = get_account_exposure(user)
        automatic_renewal = Subscription.objects.filter(user=user, cancel_at_end=False).exclude(provider_id__isnull=True).exclude(provider_id='').exists()
        
        return Response({
            "active_strategies": Strategy.objects.filter(user=user, status='ACTIVE').count(),
            "running_live_sessions": TradingSession.objects.filter(user=user, status='RUNNING').count(),
            "exposure": exposure,
            "automatic_renewal": automatic_renewal,
            "can_shutdown": not any(exposure.values()) and not automatic_renewal,
            "active_paper_accounts": PaperAccount.objects.filter(user=user, sessions__status__in=['RUNNING', 'PAUSED', 'STOPPING']).distinct().count(),
            "active_broker_connections": BrokerCredential.objects.filter(user=user, is_active=True).count(),
            "running_backtests": BacktestRun.objects.filter(user=user, status__in=['PENDING', 'RUNNING']).count(),
        })


class AccountDeactivateView(APIView):
    """Deactivate user account (set is_active=False)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from users.privacy import shutdown_account
        shutdown_account(request.user)

        response = Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )
        unset_jwt_cookies(response)
        return response


class AccountDeleteView(APIView):
    """Permanently delete user account."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        from users.privacy import shutdown_account
        shutdown_account(request.user, erase=True)

        response = Response(
            {"detail": "Account disabled and sign-in identity erased. Required payment and execution records are retained."},
            status=status.HTTP_200_OK,
        )
        # Clear the HTTP-only JWT cookies to prevent phantom session errors
        unset_jwt_cookies(response)
        return response


# ──────────────────────────────────────────────
# Email Verification Resend
# ──────────────────────────────────────────────


class ResendVerificationEmailView(AuthActionMixin, APIView):
    """Resend the email verification link."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            email_address = EmailAddress.objects.get(email=email)
            if not email_address.verified:
                email_address.send_confirmation(request._request)
        except EmailAddress.DoesNotExist:
            pass
        return Response({"message": "If this email needs verification, a verification link has been sent."})
