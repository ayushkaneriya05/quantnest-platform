from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.privacy import AccountExportView
from .views import (
    ClientErrorView,
    TicketViewSet,
)

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="customer-ticket")
urlpatterns = [
    path("", include(router.urls)),
    path("account/export/", AccountExportView.as_view()),
    path("client-errors/", ClientErrorView.as_view()),
]
