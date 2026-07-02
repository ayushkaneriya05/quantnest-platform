from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import JournalEntryViewSet, MistakeTagViewSet, TradingInsightViewSet

router = DefaultRouter()
router.register(r"entries", JournalEntryViewSet, basename="journal-entry")
router.register(r"mistake-tags", MistakeTagViewSet, basename="journal-mistake-tag")
router.register(r"insights", TradingInsightViewSet, basename="journal-insight")

urlpatterns = [path("", include(router.urls))]

