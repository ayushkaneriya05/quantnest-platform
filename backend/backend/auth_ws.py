# backend/backend/auth_ws.py
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        validated = JWTAuthentication().get_validated_token(token)
        user = JWTAuthentication().get_user(validated)
        return user
    except Exception:
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = None
        # Accept token via ?token=<JWT> or Sec-WebSocket-Protocol (optional)
        if "token" in query:
            token = query["token"][0]
        if token:
            scope["user"] = await get_user_from_token(token)
        return await super().__call__(scope, receive, send)

def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
