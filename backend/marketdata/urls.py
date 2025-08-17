# backend/marketdata/urls.py
from django.urls import path
from .views import OHLCView

urlpatterns = [
    path("ohlc/", OHLCView.as_view(), name="ohlc"),
]
