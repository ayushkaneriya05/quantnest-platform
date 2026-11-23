from collections.abc import Callable
from typing import cast
from django.urls import re_path

from .consumers import PaperTradingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/paper/$", cast(Callable, PaperTradingConsumer.as_asgi())),
]
