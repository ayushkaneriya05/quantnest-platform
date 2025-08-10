from django.contrib import admin
from django.urls import path, include

from .views import (
    CustomRegisterView,
    UserProfileView,
    TOTPCreateView,
    TOTPVerifyView,
    TOTPDisableView,
    GoogleLoginView,
    TwoStepLoginView,
    TwoFactorVerifyView,
    Get2FAStatusView,
    DeleteAvatarView,
)


urlpatterns = [
    path("auth/login/", TwoStepLoginView.as_view(), name="login"),
    path("auth/verify-2fa/", TwoFactorVerifyView.as_view(), name="otp-verify"),
    path("auth/registration/",CustomRegisterView.as_view(), name="custom_register"),
    path("2fa/create/", TOTPCreateView.as_view(), name="2fa-create"),
    path("2fa/verify/", TOTPVerifyView.as_view(), name="2fa-verify"),
    path("2fa/disable/", TOTPDisableView.as_view(), name="2fa-disable"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path(
        "auth/2fa/status/",
        Get2FAStatusView.as_view(),
        name="get-2fa-status",
    ),
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("auth/", include("dj_rest_auth.urls")),
    path("accounts/", include("allauth.urls")),
    path("avatar/delete/", DeleteAvatarView.as_view(), name="avatar-delete"),
]

from django.http import HttpResponse

def dummy_reset_confirm(request, uidb64=None, token=None):
    return HttpResponse("Password reset handled by React", content_type="text/plain")

urlpatterns += [
    path(
        'password/reset/confirm/<uidb64>/<token>/',
        dummy_reset_confirm,
        name='password_reset_confirm'
    ),
]
