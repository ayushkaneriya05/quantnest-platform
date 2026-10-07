from django.urls import include, path

from .auth_views import (
    ActiveSessionsView, BackupCodeVerifyView, CSRFTokenView,
    CustomLogoutView, CustomPasswordChangeView, CustomPasswordResetConfirmView,
    CustomPasswordResetView, CustomRegisterView, CustomTokenRefreshView,
    LogoutAllView, RevokeSessionView, TwoFactorVerifyView, TwoStepLoginView,
)
from .google_auth import GoogleCallbackView, GoogleCompleteView, GoogleStartView
from .views import (
    AccountPreflightView,
    AccountDeactivateView,
    AccountDeleteView,
    BackupCodesListView,
    BackupCodesRegenerateView,
    DeleteAvatarView,
    Get2FAStatusView,
    ResendVerificationEmailView,
    SubscriptionStatusView,
    TOTPCreateView,
    TOTPDisableView,
    TOTPVerifyView,
    UserProfileView,
)

urlpatterns = [
    # Auth
    path("auth/csrf/", CSRFTokenView.as_view(), name="auth-csrf"),
    path("auth/login/", TwoStepLoginView.as_view(), name="login"),
    path("auth/verify-2fa/", TwoFactorVerifyView.as_view(), name="otp-verify"),
    path("auth/registration/", CustomRegisterView.as_view(), name="custom_register"),
    path("auth/registration/resend-email/", ResendVerificationEmailView.as_view(), name="resend-email"),
    path("auth/password/reset/", CustomPasswordResetView.as_view(), name="rest_password_reset"),
    path("auth/password/reset/confirm/", CustomPasswordResetConfirmView.as_view(), name="rest_password_reset_confirm"),
    path("auth/password/change/", CustomPasswordChangeView.as_view(), name="rest_password_change"),
    path("auth/logout/", CustomLogoutView.as_view(), name="rest_logout"),
    path("auth/google/start/", GoogleStartView.as_view(), name="google_oauth_start"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_oauth_callback"),
    path("auth/google/complete/", GoogleCompleteView.as_view(), name="google_oauth_complete"),
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
    path("account/preflight/", AccountPreflightView.as_view(), name="account-preflight"),
    path("account/deactivate/", AccountDeactivateView.as_view(), name="account-deactivate"),
    path("account/", AccountDeleteView.as_view(), name="account-delete"),
    # dj-rest-auth & allauth (includes password change/reset, token refresh, logout, etc.)
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("auth/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/", include("dj_rest_auth.urls")),
    path("accounts/", include("allauth.urls")),
]

# Dummy view for password reset confirm — Django needs this URL name but React handles the page
from django.http import HttpResponse


def dummy_reset_confirm(request, uidb64=None, token=None):
    return HttpResponse("Password reset handled by React", content_type="text/plain")


urlpatterns += [
    path("password/reset/confirm/<uidb64>/<token>/", dummy_reset_confirm, name="password_reset_confirm"),
]
