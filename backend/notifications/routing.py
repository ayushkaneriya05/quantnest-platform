from collections.abc import Callable
from typing import cast
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', cast(Callable, consumers.NotificationConsumer.as_asgi())),
]
