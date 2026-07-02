from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

import logging
logger = logging.getLogger(__name__)

class SafeJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that checks if the token's JTI has been blacklisted.
    This ensures that 'Logout Everywhere' and 'Revoke Session' take effect immediately
    for access tokens, even before they expire.
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

        # raw_token from cookie is a string, simplejwt expects bytes
        if isinstance(raw_token, str):
            raw_token = raw_token.encode('utf-8')

        try:
            validated_token = self.get_validated_token(raw_token)
        except AuthenticationFailed:
            return None

        # Check if this token's JTI is in the blacklist
        jti = validated_token.get("jti")
        sid = validated_token.get("sid") # Session ID (Refresh Token JTI)

        # DEBUG LOGGING (Temporary)
        logger.info(f"--- Auth Check --- JTI: {jti}, SID: {sid}")

        if jti:
            if BlacklistedToken.objects.filter(token__jti=jti).exists():
                logger.warning(f"Rejecting blocked JTI: {jti}")
                raise AuthenticationFailed("This token has been revoked.", code="token_revoked")
 
        return self.get_user(validated_token), validated_token
