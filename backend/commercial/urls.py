from django.urls import path
from .views import (
    AccountView,
    CancelView,
    ChangeView,
    CheckoutView,
    InvoiceView,
    PaymentVerifyView,
    RazorpayWebhookView,
    RefundView,
    RenewalView,
)

urlpatterns = [
    path("account/", AccountView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("renew/", RenewalView.as_view()),
    path("change/", ChangeView.as_view()),
    path("cancel/", CancelView.as_view()),
    path("verify/", PaymentVerifyView.as_view()),
    path("refund-requests/", RefundView.as_view()),
    path("invoices/<int:pk>/", InvoiceView.as_view()),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view()),
]
