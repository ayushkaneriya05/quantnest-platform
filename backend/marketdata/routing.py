# backend/marketdata/routing.py
from django.urls import re_path
from marketdata.consumers import MarketDataConsumer
from trading.consumers import OrderbookConsumer

websocket_urlpatterns = [
    # Global delayed market data stream
    re_path(r'^ws/marketdata/$', MarketDataConsumer.as_asgi()),
    # Symbol-specific delayed market data stream
    re_path(r'^ws/market/(?P<symbol>[A-Za-z0-9:_-]+)/$', MarketDataConsumer.as_asgi()),
    # Paper trading orderbook stream
    re_path(r'^ws/orderbook/(?P<symbol>[A-Za-z0-9:_-]+)/$', OrderbookConsumer.as_asgi()),
]
