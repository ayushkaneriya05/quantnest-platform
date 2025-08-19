import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import marketdata.routing  # Ensure this import is present

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# This is the main router for your project
application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": get_asgi_application(),

    # WebSocket chat handler
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # This line tells Channels to look in your marketdata app for WebSocket URLs
            marketdata.routing.websocket_urlpatterns
        )
    ),
})