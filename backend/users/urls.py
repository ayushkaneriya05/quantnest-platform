from django.urls import include, path

from .views import (
    AccountPreflightView,
    AccountDeactivateView,
    AccountDeleteView,
    ActiveSessionsView,
    APIKeyDeleteView,
    APIKeyListCreateView,
    BackupCodeVerifyView,
    BackupCodesListView,
    BackupCodesRegenerateView,
    CustomLogoutView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetView,
    CustomRegisterView,
    DeleteAvatarView,
    Get2FAStatusView,
    GoogleLoginView,
    LogoutAllView,
    ResendVerificationEmailView,
    RevokeSessionView,
    SubscriptionStatusView,
    TOTPCreateView,
    TOTPDisableView,
    TOTPVerifyView,
    TwoFactorVerifyView,
    TwoStepLoginView,
    UserProfileView,
)

urlpatterns = [
    # Auth
    path("auth/login/", TwoStepLoginView.as_view(), name="login"),
    path("auth/verify-2fa/", TwoFactorVerifyView.as_view(), name="otp-verify"),
    path("auth/registration/", CustomRegisterView.as_view(), name="custom_register"),
    path("auth/registration/resend-email/", ResendVerificationEmailView.as_view(), name="resend-email"),
    path("auth/password/reset/", CustomPasswordResetView.as_view(), name="rest_password_reset"),
    path("auth/password/reset/confirm/", CustomPasswordResetConfirmView.as_view(), name="rest_password_reset_confirm"),
    path("auth/logout/", CustomLogoutView.as_view(), name="rest_logout"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/2fa/status/", Get2FAStatusView.as_view(), name="get-2fa-status"),
    path("auth/sessions/", ActiveSessionsView.as_view(), name="active-sessions"),
    path("auth/sessions/<int:pk>/", RevokeSessionView.as_view(), name="revoke-session"),
    path("auth/logout-all/", LogoutAllView.as_view(), name="logout-all"),
    # 2FA management
    path("2fa/create/", TOTPCreateView.as_view(), name="2fa-create"),
    path("2fa/verify/", TOTPVerifyView.as_view(), name="2fa-verify"),
    path("2fa/disable/", TOTPDisableView.as_view(), name="2fa-disable"),
    path("2fa/backup-codes/", BackupCodesListView.as_view(), name="backup-codes-list"),
    path("2fa/backup-codes/regenerate/", BackupCodesRegenerateView.as_view(), name="backup-codes-regenerate"),
    path("2fa/backup-codes/verify/", BackupCodeVerifyView.as_view(), name="backup-code-verify"),
    # Profile
    path("profile/", UserProfileView.as_view(), name="user_profile"),
    path("avatar/delete/", DeleteAvatarView.as_view(), name="avatar-delete"),
    # Account management
    path("subscription/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path("api-keys/", APIKeyListCreateView.as_view(), name="api-keys"),
    path("api-keys/<int:pk>/", APIKeyDeleteView.as_view(), name="api-key-delete"),
    path("account/preflight/", AccountPreflightView.as_view(), name="account-preflight"),
    path("account/deactivate/", AccountDeactivateView.as_view(), name="account-deactivate"),
    path("account/", AccountDeleteView.as_view(), name="account-delete"),
    # dj-rest-auth & allauth (includes password change/reset, token refresh, logout, etc.)
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("auth/", include("dj_rest_auth.urls")),
    path("accounts/", include("allauth.urls")),
]

# Dummy view for password reset confirm — Django needs this URL name but React handles the page
from django.http import HttpResponse


def dummy_reset_confirm(request, uidb64=None, token=None):
    return HttpResponse("Password reset handled by React", content_type="text/plain")


urlpatterns += [
    path(
        "password/reset/confirm/<uidb64>/<token>/",
        dummy_reset_confirm,
        name="password_reset_confirm",
    ),
]
