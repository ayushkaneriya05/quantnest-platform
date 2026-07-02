from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet, ComplianceCheckViewSet, StrategyApprovalViewSet

router = DefaultRouter()
router.register(r"logs", AuditLogViewSet, basename="audit-log")
router.register(r"approvals", StrategyApprovalViewSet, basename="strategy-approval")
router.register(r"compliance", ComplianceCheckViewSet, basename="compliance-check")

urlpatterns = [path("", include(router.urls))]

