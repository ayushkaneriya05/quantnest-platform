from django.urls import path
from .views import (
    RefreshLicenseView,
    LocalLicenseView,
    ResumeLicenseView,
    SupportAccessView,
    SupportDiagnosticsView,
)

urlpatterns = [
    path("refresh/", RefreshLicenseView.as_view()),
    path("local/", LocalLicenseView.as_view()),
    path("resume/", ResumeLicenseView.as_view()),
    path("support-access/", SupportAccessView.as_view()),
    path("support-access/<int:pk>/diagnostics/", SupportDiagnosticsView.as_view()),
]
