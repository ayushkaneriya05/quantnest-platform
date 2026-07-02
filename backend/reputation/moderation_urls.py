from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIModerationFlagViewSet

router = DefaultRouter()
router.register(r"ai-flags", AIModerationFlagViewSet, basename="moderation-ai-flag")

urlpatterns = [path("", include(router.urls))]

