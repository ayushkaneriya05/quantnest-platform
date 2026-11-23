# backend/marketdata/routing.py
from collections.abc import Callable
from typing import cast
from django.urls import re_path
from . import consumers

# This list tells Channels how to route WebSocket connections.
websocket_urlpatterns = [
    re_path(r'^ws/marketdata/$', cast(Callable, consumers.MarketDataConsumer.as_asgi())),
]
