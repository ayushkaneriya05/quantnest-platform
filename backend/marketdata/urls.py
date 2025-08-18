# backend/marketdata/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("fyers/login/", views.fyers_login, name="fyers_login"),
    path("fyers/callback/", views.fyers_callback, name="fyers_callback"),
    path("fyers/token/status/", views.fyers_token_status, name="fyers_token_status"),
    path("fyers/token/refresh/", views.fyers_token_refresh, name="fyers_token_refresh"),
    path("symbols/search/", views.symbol_search, name="symbol_search"), # New URL
]