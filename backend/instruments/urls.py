"""
URL configuration for the instruments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InstrumentViewSet, WatchlistInstrumentViewSet, ExecutionRouteViewSet

router = DefaultRouter()
router.register(r'instruments', InstrumentViewSet, basename='instrument')
router.register(r'watchlist', WatchlistInstrumentViewSet, basename='watchlist')
router.register(r'execution-routes', ExecutionRouteViewSet, basename='execution-route')

urlpatterns = [
    path('', include(router.urls)),
]
