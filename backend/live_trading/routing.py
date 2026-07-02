from django.urls import re_path

from .consumers import LiveTradingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/live/$", LiveTradingConsumer.as_asgi()),
]
