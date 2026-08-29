from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.core.cache import cache
from common.cache_keys import CacheKeys
import logging

logger = logging.getLogger(__name__)

class SafeJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that enforces Stateful validation via session_id.
    Ensures absolute revocation accuracy with Redis caching.
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            # Fallback to checking cookies
            from django.conf import settings
            cookie_name = getattr(settings, 'REST_AUTH', {}).get('JWT_AUTH_COOKIE', 'quantnest-auth')
            raw_token = request.COOKIES.get(cookie_name)
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        if isinstance(raw_token, str):
            raw_token = raw_token.encode('utf-8')

        try:
            validated_token = self.get_validated_token(raw_token)
        except AuthenticationFailed:
            return None

        session_id = validated_token.get("session_id")
        
        if session_id:
            cache_key = CacheKeys.AUTH_SESSION.format(session_id=session_id)
            is_valid = cache.get(cache_key)

            if is_valid is None:
                # Local import to avoid circular import errors
                from users.models import UserSession
                is_valid = UserSession.objects.filter(session_id=session_id).exists()
                cache.set(cache_key, is_valid, timeout=60)

            if not is_valid:
                logger.warning(f"Rejecting revoked session_id: {session_id}")
                raise AuthenticationFailed("This session has been revoked or expired.", code="session_revoked")
                
        return self.get_user(validated_token), validated_token
