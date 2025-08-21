from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
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
