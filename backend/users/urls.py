from django.contrib import admin
from django.urls import path, include, re_path
from allauth.account.views import confirm_email
from .views import (
    UserProfileView,
    TOTPCreateView,
    TOTPVerifyView,
    TOTPDisableView,
    GoogleLoginView,
    TwoStepLoginView,
    TwoFactorVerifyView,
    Update2FAStatusView,
)

urlpatterns = [
    # --- Authentication & Registration provided by dj-rest-auth ---
    # Includes endpoints for: login, logout, password change/reset, etc.
    path("auth/login/", TwoStepLoginView.as_view(), name="login"),
    path("auth/verify-2fa/", TwoFactorVerifyView.as_view(), name="otp-verify"),
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("2fa/create/", TOTPCreateView.as_view(), name="2fa-create"),
    path("2fa/verify/", TOTPVerifyView.as_view(), name="2fa-verify"),
    path("2fa/disable/", TOTPDisableView.as_view(), name="2fa-disable"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    # path(
    #     "auth/update-2fa-status/",
    #     Update2FAStatusView.as_view(),
    #     name="update-2fa-status",
    # ),
    # This URL is used by django-allauth for email verification
    re_path(
        r"^account-confirm-email/(?P<key>[-:\w]+)/$",
        confirm_email,
        name="account_confirm_email",
    ),
    # --- Custom User Profile Endpoint ---
    path("profile/", UserProfileView.as_view(), name="user_profile"),
]
