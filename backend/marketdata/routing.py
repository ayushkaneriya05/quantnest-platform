# backend/marketdata/routing.py
from django.urls import re_path
from marketdata.consumers import MarketDataConsumer
from trading.consumers import OrderbookConsumer

websocket_urlpatterns = [
    re_path(r'^ws/marketdata/$', MarketDataConsumer.as_asgi()),                     # global delayed
    re_path(r'^ws/market/(?P<symbol>[A-Za-z0-9:_-]+)/$', MarketDataConsumer.as_asgi()),  # per-symbol delayed
    re_path(r'^ws/orderbook/(?P<symbol>[A-Za-z0-9:_-]+)/$', OrderbookConsumer.as_asgi()),# orderbook
]
