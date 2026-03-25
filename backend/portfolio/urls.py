"""
URL routing for the portfolio app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolio')
router.register(r'allocations', views.CapitalAllocationViewSet, basename='allocation')
router.register(r'transactions', views.FundTransactionViewSet, basename='transaction')
router.register(r'exposure', views.ExposureSnapshotViewSet, basename='exposure')
router.register(r'performance', views.DailyPerformanceViewSet, basename='performance')

urlpatterns = [
    path('', include(router.urls)),
]
