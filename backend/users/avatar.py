"""Short-lived image capabilities avoid making the media volume public."""
import mimetypes
from pathlib import PurePath

from django.core import signing
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class AvatarView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            claims = signing.loads(request.query_params.get("token", ""), salt="profile-avatar", max_age=1800)
            user = get_user_model().objects.get(pk=claims["user"], is_active=True)
            if not user.avatar or user.avatar.name != claims["name"]:
                raise NotFound()
            # Avatars are small; buffer them in the synchronous view's worker thread.
            with user.avatar.open("rb") as image:
                content = image.read()
        except (signing.BadSignature, KeyError, TypeError, ValueError, FileNotFoundError, get_user_model().DoesNotExist):
            raise NotFound("This image link is unavailable or expired.")
        response = HttpResponse(
            content,
            content_type=mimetypes.guess_type(user.avatar.name)[0] or "application/octet-stream",
        )
        response["Content-Length"] = len(content)
        response["Content-Disposition"] = content_disposition_header(False, PurePath(user.avatar.name).name)
        response["Cache-Control"] = "private, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response
