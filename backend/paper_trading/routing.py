from django.urls import re_path

from .consumers import PaperTradingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/paper/$", PaperTradingConsumer.as_asgi()),
]
