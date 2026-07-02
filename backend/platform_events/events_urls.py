from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DomainEventViewSet

router = DefaultRouter()
router.register(r"", DomainEventViewSet, basename="domain-event")

urlpatterns = [path("", include(router.urls))]

