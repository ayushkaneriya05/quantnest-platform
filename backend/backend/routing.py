from django.urls import re_path
from marketdata.consumers import MarketDataConsumer

websocket_urlpatterns = [
    re_path(r"ws/marketdata/$", MarketDataConsumer.as_asgi()),
]
