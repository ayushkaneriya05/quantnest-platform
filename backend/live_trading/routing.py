from collections.abc import Callable
from typing import cast
from django.urls import re_path

from .consumers import LiveTradingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/live/$", cast(Callable, LiveTradingConsumer.as_asgi())),
]
