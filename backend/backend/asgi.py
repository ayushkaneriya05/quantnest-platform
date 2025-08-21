import os
import django
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import marketdata.routing
from .middleware.jwt_auth import JWTAuthMiddleware

django_asgi_app = get_asgi_application()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            marketdata.routing.websocket_urlpatterns
        )
    ),
})
