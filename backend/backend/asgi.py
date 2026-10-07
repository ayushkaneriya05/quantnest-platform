import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
import marketdata.routing
import live_trading.routing
import paper_trading.routing
import backtesting.routing
import notifications.routing
import research.routing
from .middleware.jwt_auth import JWTAuthMiddleware



django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": OriginValidator(JWTAuthMiddleware(
        URLRouter(
            marketdata.routing.websocket_urlpatterns + 
            live_trading.routing.websocket_urlpatterns +
            paper_trading.routing.websocket_urlpatterns +
            backtesting.routing.websocket_urlpatterns +
            notifications.routing.websocket_urlpatterns +
            research.routing.websocket_urlpatterns
        )
    ), settings.CORS_ALLOWED_ORIGINS),
})
