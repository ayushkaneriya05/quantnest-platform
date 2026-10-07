from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from dj_rest_auth.app_settings import api_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from users.authentication import SafeJWTAuthentication


class JWTAuthMiddleware:
    """WebSockets enforce the same user, password and session checks as REST."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()
        headers = dict(scope.get("headers", []))
        cookies = SimpleCookie(headers.get(b"cookie", b"").decode())
        cookie = cookies.get(api_settings.JWT_AUTH_COOKIE)
        if cookie:
            try:
                token = AccessToken(cookie.value)
                scope["user"] = await database_sync_to_async(SafeJWTAuthentication().get_user)(token)
                scope["auth_session_id"] = token["session_id"]
                scope["auth_expires_at"] = token["exp"]
                scope["auth_token"] = token
            except (TokenError, AuthenticationFailed):
                pass
        return await self.inner(scope, receive, send)
