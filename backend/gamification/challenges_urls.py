from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChallengeViewSet

router = DefaultRouter()
router.register(r"", ChallengeViewSet, basename="public-challenge")

urlpatterns = [path("", include(router.urls))]
