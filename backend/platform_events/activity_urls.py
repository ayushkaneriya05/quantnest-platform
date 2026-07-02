from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityEventViewSet

router = DefaultRouter()
router.register(r"", ActivityEventViewSet, basename="activity-event")

urlpatterns = [path("", include(router.urls))]

