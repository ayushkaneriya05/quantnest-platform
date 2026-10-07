from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResearchRunViewSet, ResearchSessionViewSet, ResearchActionViewSet, research_schema, research_tool

router = DefaultRouter()
router.register("sessions", ResearchSessionViewSet, basename="research-session")
router.register("runs", ResearchRunViewSet, basename="research-run")
router.register("actions", ResearchActionViewSet, basename="research-action")
urlpatterns = [path("schema/", research_schema), path("tools/", research_tool), path("", include(router.urls))]
