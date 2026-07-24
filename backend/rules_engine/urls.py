"""
URL configuration for the rules_engine app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TimeRuleViewSet, SpecialEventFilterViewSet, RuleGroupViewSet,
    RuleViewSet
)

router = DefaultRouter()
router.register(r'time-rules', TimeRuleViewSet, basename='time-rule')
router.register(r'event-filters', SpecialEventFilterViewSet, basename='event-filter')
router.register(r'rule-groups', RuleGroupViewSet, basename='rule-group')
router.register(r'rules', RuleViewSet, basename='rule')


urlpatterns = [
    path('', include(router.urls)),
]
