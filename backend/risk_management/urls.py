"""
URL routing for the risk_management app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sizing', views.PositionSizingRuleViewSet, basename='sizing')
router.register(r'auto-disable', views.StrategyAutoDisableViewSet, basename='auto-disable')

urlpatterns = [
    path('', include(router.urls)),
]
