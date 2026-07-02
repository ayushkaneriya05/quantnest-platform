"""
URL routing for the risk_management app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sizing', views.PositionSizingRuleViewSet, basename='sizing')
router.register(r'profile', views.PortfolioRiskProfileViewSet, basename='profile')
router.register(r'auto-disable', views.StrategyAutoDisableViewSet, basename='auto-disable')
router.register(r'violations', views.RiskViolationViewSet, basename='violations')

urlpatterns = [
    path('', include(router.urls)),
]
