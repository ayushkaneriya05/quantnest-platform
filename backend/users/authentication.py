from datetime import timedelta

from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from .models import UserSession
from .sessions import token_session_id


class SafeJWTAuthentication(JWTCookieAuthentication):
    """Require an active, owned session for bearer and cookie authentication."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        now = timezone.now()
        session = UserSession.objects.filter(
            session_id=token_session_id(validated_token), user=user, expires_at__gt=now,
        ).only("id", "last_activity").first()
        if session is None:
            raise AuthenticationFailed("This session has ended. Please sign in again.", code="session_revoked")
        if session.last_activity < now - timedelta(minutes=1):
            UserSession.objects.filter(pk=session.pk, last_activity=session.last_activity).update(last_activity=now)
        return user
