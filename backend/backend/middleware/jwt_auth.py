from urllib.parse import parse_qs
from http.cookies import SimpleCookie
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = None
        
        # 1. Try to get token from HttpOnly cookie
        headers = dict(scope.get("headers", []))
        if b"cookie" in headers:
            cookie = SimpleCookie(headers[b"cookie"].decode())
            cookie_name = getattr(settings, "REST_AUTH", {}).get("JWT_AUTH_COOKIE", "quantnest-auth")
            if cookie_name in cookie:
                token = cookie[cookie_name].value

        # 2. Fallback to query string
        if not token:
            query_string = parse_qs(scope.get("query_string", b"").decode())
            token = query_string.get("token", [None])[0]

        scope["user"] = AnonymousUser()

        if token:
            try:
                UntypedToken(token)  # validate token
                user = await self.get_user_from_token(token)
                if user:
                    scope["user"] = user
            except (InvalidToken, TokenError):
                pass

        # ✅ Pass scope, receive, and send properly
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
        except Exception:
            return None


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
