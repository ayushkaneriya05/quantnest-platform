# backend/marketdata/urls.py
from django.urls import path
from . import oauth, views

urlpatterns = [
    path("fyers/login/", oauth.fyers_login, name="fyers_login"),
    path("fyers/callback/", oauth.fyers_callback, name="fyers_callback"),
    path("fyers/token/status/", oauth.fyers_token_status, name="fyers_token_status"),
    path("candles/", views.candles, name="candles"),
    path("latest-tick/", views.latest_tick_data, name="latest_tick_data"),
    path("quotes/", views.quote_snapshots, name="quote_snapshots"),
]
