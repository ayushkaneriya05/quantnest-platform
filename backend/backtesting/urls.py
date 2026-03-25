"""
URL routing for the backtesting app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'runs', views.BacktestRunViewSet, basename='backtest-run')
router.register(r'optimization', views.OptimizationRunViewSet, basename='optimization')
router.register(r'montecarlo', views.MonteCarloRunViewSet, basename='montecarlo')

urlpatterns = [
    path('', include(router.urls)),
]
