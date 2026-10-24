"""
URL routing for the paper_trading app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.PaperSessionViewSet, basename='paper-session')
router.register(r'accounts', views.PaperAccountViewSet, basename='paper-account')
router.register(r'positions', views.PaperPositionViewSet, basename='paper-position')
router.register(r'orders', views.PaperOrderViewSet, basename='paper-order')
router.register(r'trades', views.PaperTradeViewSet, basename='paper-trade')

# Simulated wallet and fund history
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolio')
router.register(r'transactions', views.FundTransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
]
