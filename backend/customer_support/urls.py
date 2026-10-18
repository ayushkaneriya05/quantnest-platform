from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.privacy import AccountExportView
from .views import (
    BrevoWebhookView,
    ClientErrorView,
    ConsentView,
    InboundEmailView,
    MilestoneCheckoutView,
    NewsletterConfirmView,
    QuoteAcceptView,
    QuoteListView,
    TicketViewSet,
)

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="customer-ticket")
urlpatterns = [
    path("", include(router.urls)),
    path("consent/", ConsentView.as_view()),
    path("newsletter/confirm/", NewsletterConfirmView.as_view()),
    path("webhooks/brevo/", BrevoWebhookView.as_view()),
    path("webhooks/brevo-inbound/", InboundEmailView.as_view()),
    path("quotations/", QuoteListView.as_view()),
    path("quotations/<int:pk>/accept/", QuoteAcceptView.as_view()),
    path("milestones/<int:pk>/checkout/", MilestoneCheckoutView.as_view()),
    path("account/export/", AccountExportView.as_view()),
    path("client-errors/", ClientErrorView.as_view()),
]
