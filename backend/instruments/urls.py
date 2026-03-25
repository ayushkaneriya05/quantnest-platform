"""
URL configuration for the instruments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InstrumentViewSet, WatchlistInstrumentViewSet

router = DefaultRouter()
router.register(r'instruments', InstrumentViewSet, basename='instrument')
router.register(r'watchlist', WatchlistInstrumentViewSet, basename='watchlist')

urlpatterns = [
    path('', include(router.urls)),
]
