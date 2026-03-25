"""
URL configuration for the strategies app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StrategyViewSet, StrategyTagViewSet, EntryOrderConfigViewSet, ExitOrderConfigViewSet, ReEntryRuleViewSet

router = DefaultRouter()
router.register(r'strategies', StrategyViewSet, basename='strategy')
router.register(r'tags', StrategyTagViewSet, basename='strategy-tag')
router.register(r'entry-configs', EntryOrderConfigViewSet, basename='entry-config')
router.register(r'exit-configs', ExitOrderConfigViewSet, basename='exit-config')
router.register(r'reentry-rules', ReEntryRuleViewSet, basename='reentry-rule')

urlpatterns = [
    path('', include(router.urls)),
]
