# backend/marketdata/routing.py
from django.urls import re_path
from . import consumers

# This list tells Channels how to route WebSocket connections.
websocket_urlpatterns = [
    # It maps the URL 'ws/marketdata/' to the MarketDataConsumer.
    re_path(r'^ws/marketdata/$', consumers.MarketDataConsumer.as_asgi()),
]