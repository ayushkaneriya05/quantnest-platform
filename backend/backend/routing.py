from django.urls import re_path
from marketdata.consumers import MarketDataConsumer
from trading.consumers import OrderbookConsumer

websocket_urlpatterns = [
    re_path(r"ws/marketdata/$", MarketDataConsumer.as_asgi()),
    re_path(r"ws/orderbook/(?P<symbol>\w+)/$", OrderbookConsumer.as_asgi()),
]