# backend/marketdata/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Fyers authentication endpoints
    path("fyers/login/", views.fyers_login, name="fyers_login"),
    path("fyers/callback/", views.fyers_callback, name="fyers_callback"),
    path("fyers/token/status/", views.fyers_token_status, name="fyers_token_status"),
    path("fyers/token/refresh/", views.fyers_token_refresh, name="fyers_token_refresh"),

    # Market data endpoints
    path("ohlc/", views.ohlc_data, name="ohlc_data"),
    path("live-price/", views.live_price, name="live_price"),
    path("historical/", views.historical_data, name="historical_data"),
]
