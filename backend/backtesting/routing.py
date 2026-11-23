from collections.abc import Callable
from typing import cast
from django.urls import re_path
from .consumers import BacktestProgressConsumer

websocket_urlpatterns = [
    re_path(r"^ws/backtest/progress/$", cast(Callable, BacktestProgressConsumer.as_asgi())),
]
