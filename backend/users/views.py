from rest_framework import generics, status, throttling
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
import logging
from .serializers import UserProfileSerializer
from rest_framework.views import APIView
from rest_framework import status
import qrcode
import qrcode.image.svg
from io import BytesIO

logger = logging.getLogger(__name__)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.contrib.auth import get_user_model

User = get_user_model()

from dj_rest_auth.views import LoginView
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice


class TwoStepLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        user = self.user

        # If user has OTP device confirmed
        otp_devices = [device for device in devices_for_user(user) if device.confirmed]

        if otp_devices:
            # Logout user and ask for OTP code
            from django.contrib.auth import logout

            logout(request)

            # Instead of returning token, say 2FA is required
            return Response(
                {
                    "is_2fa_required": True,
                    "detail": "Two-factor authentication is required.",
                    "user_id": user.id,
                },
                status=status.HTTP_200_OK,
            )

        # If no 2FA → allow login
        return response


class TwoFactorVerifyView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        otp_token = request.data.get("otp_token")
        print(f"Verifying OTP for user {user_id} with token {otp_token}")
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid user"}, status=400)

        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device and device.verify_token(otp_token):
            # Token is correct → return login tokens
            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "user": {"email": user.email, "username": user.username},
                }
            )

        return Response({"error": "Invalid OTP token"}, status=400)


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:5173/google-callback"
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            # Log the incoming request data for debugging
            print("Incoming request data:", request.data)
            return super().post(request, *args, **kwargs)
        except Exception as e:
            import traceback

            print("Google login error:", str(e))
            traceback.print_exc()


class TOTPCreateView(APIView):
    """View to create and return a new TOTP device for the user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # Get all existing devices for the user
        device = user.totpdevice_set.filter(confirmed=False).first()

        # If no unconfirmed device exists, create a new one.
        if not device:
            # Before creating a new one, delete any old devices to ensure a clean state.
            for old_device in devices_for_user(user):
                old_device.delete()
            device = user.totpdevice_set.create(confirmed=False)
        print(f"Created new TOTP device for user {user.username} with key {device.key}")
        # Generate a QR code for the user to scan
        qr_code_url = device.config_url
        image_factory = qrcode.image.svg.SvgImage
        qr_code_image = qrcode.make(qr_code_url, image_factory=image_factory)

        # Convert the SVG image to a string to send in the response
        stream = BytesIO()
        qr_code_image.save(stream)

        return Response(
            {"qr_code": stream.getvalue().decode("utf-8"), "secret_key": device.key},
            status=status.HTTP_201_CREATED,
        )


class TOTPVerifyView(APIView):
    """View to verify and confirm the TOTP device."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        token = request.data.get("token")

        if token is None:
            return Response(
                {"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the unconfirmed device
        device = user.totpdevice_set.filter(confirmed=False).first()
        if device is None:
            return Response(
                {"error": "No unconfirmed device found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the token
        print(f"Verifying token {token} for device {device.key}")
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            print("Token verified and device confirmed.")
            return Response(
                {"success": "2FA has been enabled."}, status=status.HTTP_200_OK
            )

        return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


class TOTPDisableView(APIView):
    """View to disable 2FA for the user."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        devices = devices_for_user(user)
        for device in devices:
            device.delete()
        return Response(
            {"success": "2FA has been disabled."}, status=status.HTTP_200_OK
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating the logged-in user's profile.
    Only accessible by authenticated users.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [throttling.UserRateThrottle]

    def get_object(self):
        # This ensures users can only see and edit their own profile
        return self.request.user

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in profile update: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in profile update: {e}")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
