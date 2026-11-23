from collections.abc import Callable
from typing import cast
from django.urls import path

from .consumers import ResearchConsumer

websocket_urlpatterns = [path("ws/research/", cast(Callable, ResearchConsumer.as_asgi()))]
