# backend/ohlc/urls.py
from django.urls import path
from .views import OHLCListView

urlpatterns = [
    path('', OHLCListView.as_view(), name='ohlc-list'),
]