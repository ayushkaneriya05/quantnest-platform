from rest_framework.routers import DefaultRouter
from .views import ExecutionReportViewSet

router = DefaultRouter()
router.register("reports", ExecutionReportViewSet, basename="execution-report")
urlpatterns = router.urls

