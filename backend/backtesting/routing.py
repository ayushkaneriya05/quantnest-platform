from django.urls import re_path
from .consumers import BacktestProgressConsumer

websocket_urlpatterns = [
    re_path(r"^ws/backtest/progress/$", BacktestProgressConsumer.as_asgi()),
]
