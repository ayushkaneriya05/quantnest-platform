# backend/backend/asgi.py
from channels.routing import ProtocolTypeRouter, URLRouter
# replace AuthMiddlewareStack with our JWT stack
from backend.auth_ws import JwtAuthMiddlewareStack
import backend.routing
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddlewareStack(URLRouter(backend.routing.websocket_urlpatterns)),
})
