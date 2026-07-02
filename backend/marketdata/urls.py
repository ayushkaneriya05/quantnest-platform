# backend/marketdata/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("fyers/login/", views.fyers_login, name="fyers_login"),
    path("fyers/callback/", views.fyers_callback, name="fyers_callback"),
    path("fyers/token/status/", views.fyers_token_status, name="fyers_token_status"),
    path("fyers/token/refresh/", views.fyers_token_refresh, name="fyers_token_refresh"),
    path("candles/", views.candles, name="candles"),
    path("ohlc/", views.ohlc_data, name="ohlc_data"),
    path("latest-tick/", views.latest_tick_data, name="latest_tick_data"),
    path("live/quote/", views.live_quote, name="live_quote"),
    path("live/indices/", views.live_indices, name="live_indices"),
    path("events/", views.market_events, name="market_events"),
]
