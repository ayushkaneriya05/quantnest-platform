from rest_framework import generics, status, throttling
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
import logging
from .models import User
from .serializers import UserProfileSerializer
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.views import APIView
from rest_framework import status
import qrcode
import qrcode.image.svg
from io import BytesIO

logger = logging.getLogger(__name__)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


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
        devices = devices_for_user(user)
        # If a device already exists, delete it
        for device in devices:
            device.delete()

        # Create a new device
        device = user.totpdevice_set.create(confirmed=False)

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
        if device.verify_token(token):
            device.confirmed = True
            device.save()
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
