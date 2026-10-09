import time
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.test import TestCase
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from dj_rest_auth.app_settings import api_settings as auth_settings

from .google_auth import STATE_COOKIE, RESULT_COOKIE
from .models import BackupCode, UserSession
from .tokens import CustomRefreshToken

REFRESH_COOKIE = auth_settings.JWT_AUTH_REFRESH_COOKIE
AUTH = "/api/v1/users/auth/"
PASSWORD = "Test-Account-Password-2026!"
AGENT = "Mozilla/5.0 (Windows NT 10.0) Chrome/140.0.0.0 Safari/537.36"


class AuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="auth-user", email="auth@example.com", password=PASSWORD)
        self.client = APIClient()

    def login(self, client=None):
        client = client or self.client
        response = client.post(AUTH + "login/", {"username": self.user.username, "password": PASSWORD}, format="json", HTTP_USER_AGENT=AGENT)
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_login_issues_owned_session_and_http_only_refresh(self):
        response = self.login()
        self.assertNotIn("refresh", response.data)
        self.assertTrue(response.cookies[REFRESH_COOKIE]["httponly"])
        self.assertTrue(response.cookies[REFRESH_COOKIE]["secure"])
        self.assertEqual(response.cookies[REFRESH_COOKIE]["path"], "/api/v1/users/")
        session = UserSession.objects.get(user=self.user)
        token = AccessToken(response.data["access"])
        self.assertEqual(token["session_id"], str(session.session_id))
        self.assertEqual(session.browser, "Chrome")
        self.assertEqual(session.os, "Windows")

    def test_reload_ignores_obsolete_refresh_cookies_with_duplicate_paths(self):
        self.login()
        valid_refresh = self.client.cookies[REFRESH_COOKIE].value
        reloaded = APIClient()
        response = reloaded.post(AUTH + "token/refresh/", {}, format="json", HTTP_COOKIE=(
            f"{REFRESH_COOKIE}={valid_refresh}; quantnest-refresh=obsolete-narrow; quantnest-refresh=obsolete-root"
        ))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.cookies[REFRESH_COOKIE].value, valid_refresh)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

    def test_csrf_bootstrap_reports_cookie_presence_without_authentication(self):
        response = self.client.get(AUTH + "csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_refresh_cookie"])
        self.login()
        self.assertTrue(self.client.get(AUTH + "csrf/").data["has_refresh_cookie"])

    def test_avatar_url_upload_preservation_and_removal(self):
        from io import BytesIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from PIL import Image
        from django.conf import settings
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        with TemporaryDirectory(prefix="auth-avatar-", dir=settings.BASE_DIR) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(settings.BASE_DIR.resolve()))
            with override_settings(MEDIA_ROOT=directory):
                login = self.login()
                self.client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
                buffer = BytesIO()
                Image.new("RGB", (2, 2), color="blue").save(buffer, format="PNG")
                image = SimpleUploadedFile("avatar.png", buffer.getvalue(), content_type="image/png")
                uploaded = self.client.patch("/api/v1/users/profile/", {"avatar": image}, format="multipart")
                self.assertEqual(uploaded.status_code, 200, uploaded.data)
                self.assertTrue(uploaded.data["avatar"].startswith("http://testserver/media/avatars/"))
                self.assertEqual(self.login().data["user"]["avatar"], uploaded.data["avatar"])
                edited = self.client.patch("/api/v1/users/profile/", {"bio": "Updated profile biography"}, format="multipart")
                self.assertEqual(edited.status_code, 200, edited.data)
                self.assertEqual(edited.data["avatar"], uploaded.data["avatar"])
                self.user.refresh_from_db()
                storage, name = self.user.avatar.storage, self.user.avatar.name
                removed = self.client.patch("/api/v1/users/profile/", {"avatar": ""}, format="multipart")
                self.assertEqual(removed.status_code, 200, removed.data)
                self.assertIsNone(removed.data["avatar"])
                self.assertFalse(storage.exists(name))

    def test_auth_throttles_are_isolated_and_ignore_untrusted_forwarded_ips(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from .auth_views import LoginThrottle, SecurityActionThrottle, TwoFAVerifyThrottle

        request = Request(APIRequestFactory().post("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="198.51.100.1"))
        login = LoginThrottle()
        self.assertEqual(login.get_ident(request), "192.0.2.1")
        self.assertNotEqual(login.get_cache_key(request, None), TwoFAVerifyThrottle().get_cache_key(request, None))
        self.assertNotEqual(login.get_cache_key(request, None), SecurityActionThrottle().get_cache_key(request, None))

    def test_repeat_login_reuses_browser_session_and_invalidates_previous_refresh(self):
        self.login()
        previous = self.client.cookies[REFRESH_COOKIE].value
        sid = UserSession.objects.get().session_id
        self.login()
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(UserSession.objects.get().session_id, sid)
        with self.assertRaises(TokenError):
            CustomRefreshToken(previous)

    def test_different_browser_profiles_create_independent_sessions(self):
        self.login()
        self.login(APIClient())
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)

    def test_rotation_updates_cookies_without_creating_sessions(self):
        self.login()
        previous = self.client.cookies[REFRESH_COOKIE].value
        sid = UserSession.objects.get().session_id
        response = self.client.post(AUTH + "token/refresh/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        current = self.client.cookies[REFRESH_COOKIE].value
        self.assertNotEqual(current, previous)
        self.assertNotIn("refresh", response.data)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(UserSession.objects.get().session_id, sid)
        self.assertEqual(CustomRefreshToken(current)["session_id"], str(sid))
        with self.assertRaises(TokenError):
            CustomRefreshToken(previous)

    def test_replayed_refresh_does_not_destroy_new_session(self):
        self.login()
        previous = self.client.cookies[REFRESH_COOKIE].value
        self.client.post(AUTH + "token/refresh/", {}, format="json")
        replay = APIClient()
        replay.cookies[REFRESH_COOKIE] = previous
        self.assertEqual(replay.post(AUTH + "token/refresh/", {}).status_code, 401)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 200)

    def test_expired_session_rejects_access_and_refresh(self):
        response = self.login()
        UserSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 401)

    def test_missing_or_revoked_session_cannot_be_recreated_by_refresh(self):
        response = self.login()
        UserSession.objects.all().delete()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 401)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_access_token_without_session_claim_is_rejected(self):
        token = CustomRefreshToken.for_user(self.user)
        del token["session_id"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)

    def test_session_cannot_be_used_by_another_user(self):
        self.login()
        other = get_user_model().objects.create_user(username="other", email="other@example.com", password=PASSWORD)
        token = CustomRefreshToken.for_user(other)
        token["session_id"] = str(UserSession.objects.get(user=self.user).session_id)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)

    def test_inactive_user_cannot_refresh(self):
        self.login()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 401)

    def test_other_sessions_action_preserves_current_refresh(self):
        response = self.login()
        other = APIClient()
        self.login(other)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        result = self.client.post(AUTH + "logout-all/", {})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["revoked_count"], 1)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 200)
        self.assertEqual(other.post(AUTH + "token/refresh/", {}).status_code, 401)

    def test_session_list_current_first_and_prunes_expired(self):
        response = self.login()
        self.login(APIClient())
        UserSession.objects.create(user=self.user, expires_at=timezone.now() - timedelta(days=1), refresh_jti="expired")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        result = self.client.get(AUTH + "sessions/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data["sessions"]), 2)
        self.assertTrue(result.data["sessions"][0]["is_current"])
        self.assertEqual(UserSession.objects.count(), 2)

    def test_logout_is_idempotent_and_revokes_access(self):
        response = self.login()
        self.assertEqual(self.client.post(AUTH + "logout/", {}).status_code, 200)
        self.assertEqual(UserSession.objects.count(), 0)
        self.assertEqual(self.client.post(AUTH + "logout/", {}).status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)

    def test_forged_logout_cannot_revoke_another_session(self):
        self.login()
        legitimate = self.client.cookies[REFRESH_COOKIE].value
        segments = legitimate.split(".")
        signature = segments[2]
        segments[2] = ("A" if signature[0] != "A" else "B") + signature[1:]
        attacker = APIClient()
        attacker.cookies[REFRESH_COOKIE] = ".".join(segments)
        self.assertEqual(attacker.post(AUTH + "logout/", {}).status_code, 200)
        self.assertEqual(UserSession.objects.count(), 1)

    def test_logout_ends_session_when_refresh_rotates_after_token_validation(self):
        from rest_framework.test import APIRequestFactory
        from .sessions import refresh_session

        self.login()

        def rotate_after_validation(raw_token):
            validated = CustomRefreshToken(raw_token)
            refresh_session(APIRequestFactory().post("/"), raw_token)
            return validated

        with patch("users.auth_views.CustomRefreshToken", side_effect=rotate_after_validation):
            response = self.client.post(AUTH + "logout/", {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_password_change_requires_current_password_and_revokes_other_sessions(self):
        response = self.login()
        other = APIClient()
        self.login(other)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        payload = {"old_password": "wrong", "new_password1": "Changed-Password-2026!", "new_password2": "Changed-Password-2026!"}
        self.assertEqual(self.client.post(AUTH + "password/change/", payload).status_code, 400)
        payload["old_password"] = PASSWORD
        result = self.client.post(AUTH + "password/change/", payload)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + result.data["access"])
        self.assertEqual(self.client.get("/api/v1/users/profile/").status_code, 200)
        self.assertEqual(other.post(AUTH + "token/refresh/", {}).status_code, 401)
        self.assertEqual(self.client.post(AUTH + "token/refresh/", {}).status_code, 200)

    def test_two_factor_and_backup_challenge_are_single_use(self):
        TOTPDevice.objects.create(user=self.user, confirmed=True)
        raw_code, code_hash = BackupCode.generate_codes(1)[0]
        BackupCode.objects.create(user=self.user, code_hash=code_hash)
        login = self.login()
        self.assertTrue(login.data["is_2fa_required"])
        self.assertNotIn("access", login.data)
        self.assertEqual(UserSession.objects.count(), 0)
        payload = {"login_token": login.data["login_token"], "backup_code": raw_code.replace("-", "")}
        result = self.client.post("/api/v1/users/2fa/backup-codes/verify/", payload)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertTrue(BackupCode.objects.get().is_used)
        self.assertEqual(self.client.post("/api/v1/users/2fa/backup-codes/verify/", payload).status_code, 400)

    def test_google_login_enforces_local_two_factor(self):
        TOTPDevice.objects.create(user=self.user, confirmed=True)
        self.google_callback()
        response = self.client.post(AUTH + "google/complete/", {})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_2fa_required"])
        self.assertEqual(UserSession.objects.count(), 0)

    def test_google_login_uses_shared_session_issuance(self):
        self.google_callback()
        response = self.client.post(AUTH + "google/complete/", {})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("refresh", response.data)
        self.assertEqual(UserSession.objects.count(), 1)

    def google_start(self, next_path="/overview"):
        site, _ = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={"domain": "quantnest.test", "name": "QuantNest"})
        app, _ = SocialApp.objects.get_or_create(provider="google", defaults={"name": "Google", "client_id": "test-client", "secret": "test-secret"})
        app.sites.add(site)
        response = self.client.post(AUTH + "google/start/", {"next": next_path}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return parse_qs(urlparse(response.data["authorization_url"]).query), response

    def google_callback(self, next_path="/overview"):
        params, _ = self.google_start(next_path)
        with patch("users.google_auth._google_user", return_value=self.user):
            response = self.client.get(AUTH + "google/callback/", {"state": params["state"][0], "code": "test-code"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], settings.FRONTEND_URL.rstrip("/") + "/google-callback")
        self.assertEqual(UserSession.objects.count(), 0)
        self.assertNotIn(REFRESH_COOKIE, response.cookies)
        self.assertNotIn("_auth_user_id", self.client.session)
        return response

    def test_google_redirect_uses_state_pkce_and_backend_callback(self):
        params, response = self.google_start()
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertIn("openid", params["scope"][0])
        self.assertEqual(params["redirect_uri"], [settings.BACKEND_URL.rstrip("/") + AUTH + "google/callback/"])
        cookie = response.cookies[STATE_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], 300)

    def test_google_completion_is_single_use_and_preserves_return_path(self):
        self.google_callback("/backtests")
        cookie = self.client.cookies[RESULT_COOKIE].value
        response = self.client.post(AUTH + "google/complete/", {})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["next"], "/backtests")
        self.client.cookies[RESULT_COOKIE] = cookie
        self.assertEqual(self.client.post(AUTH + "google/complete/", {}).status_code, 400)
        self.assertEqual(UserSession.objects.count(), 1)

    def test_google_state_is_browser_bound_and_replay_is_blocked(self):
        params, _ = self.google_start()
        state_cookie = self.client.cookies[STATE_COOKIE].value
        query = {"state": params["state"][0], "code": "test-code"}
        other = APIClient()
        with patch("users.google_auth._google_user", return_value=self.user) as resolve:
            other.get(AUTH + "google/callback/", query)
            self.assertEqual(other.post(AUTH + "google/complete/", {}).status_code, 400)
            resolve.assert_not_called()
            self.client.get(AUTH + "google/callback/", query)
            resolve.assert_called_once()
            self.client.cookies[STATE_COOKIE] = state_cookie
            self.client.get(AUTH + "google/callback/", query)
            self.assertEqual(resolve.call_count, 1)

    def test_google_cancellation_and_wrong_state_do_not_issue_sessions(self):
        for query in ({"error": "access_denied"}, {"state": "wrong", "code": "test-code"}):
            params, _ = self.google_start()
            if "error" in query:
                query["state"] = params["state"][0]
            with patch("users.google_auth._google_user") as resolve:
                self.client.get(AUTH + "google/callback/", query)
                response = self.client.post(AUTH + "google/complete/", {})
                self.assertEqual(response.status_code, 400)
                self.assertIn("message", response.data)
                resolve.assert_not_called()
        self.assertEqual(UserSession.objects.count(), 0)

    def test_google_rejects_external_return_paths_and_old_token_endpoint(self):
        for next_path in ("https://evil.test/", "//evil.test/", "/\\evil.test/", None):
            self.assertEqual(self.client.post(AUTH + "google/start/", {"next": next_path}, format="json").status_code, 400)
        self.assertEqual(self.client.post(AUTH + "google/", {"access_token": "old-token"}).status_code, 404)

    def test_google_state_expiry_and_cookie_tampering(self):
        params, _ = self.google_start()
        query = {"state": params["state"][0], "code": "test-code"}
        with patch("django.core.signing.time.time", return_value=time.time() + 301), patch("users.google_auth._google_user") as resolve:
            self.client.get(AUTH + "google/callback/", query)
            resolve.assert_not_called()
        self.assertEqual(self.client.post(AUTH + "google/complete/", {}).status_code, 400)
        self.google_callback()
        self.client.cookies[RESULT_COOKIE] = "tampered-cookie"
        self.assertEqual(self.client.post(AUTH + "google/complete/", {}).status_code, 400)

    def test_google_pending_login_rejects_password_change_or_deactivation(self):
        self.google_callback()
        self.user.set_password("Changed-Password-2026!")
        self.user.save(update_fields=["password"])
        self.assertEqual(self.client.post(AUTH + "google/complete/", {}).status_code, 401)
        self.google_callback()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.client.post(AUTH + "google/complete/", {}).status_code, 401)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_google_cookie_actions_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        for route in ("google/start/", "google/complete/"):
            self.assertEqual(client.post(AUTH + route, {}).status_code, 403)

    def test_google_code_exchange_registers_verified_account_without_django_login(self):
        params, _ = self.google_start()
        profile = {"id": "google-new-user", "email": "new-google@example.com", "verified_email": True, "given_name": "Google"}
        with patch("users.google_auth.OAuth2Client.get_access_token", return_value={"access_token": "provider-token"}) as exchange, patch("users.google_auth.GoogleOAuth2Adapter._fetch_user_info", return_value=profile):
            self.client.get(AUTH + "google/callback/", {"state": params["state"][0], "code": "test-code"})
        self.assertEqual(exchange.call_args.args, ("test-code",))
        self.assertGreater(len(exchange.call_args.kwargs["pkce_code_verifier"]), 43)
        user = get_user_model().objects.get(email=profile["email"])
        self.assertFalse(user.has_usable_password())
        self.assertTrue(SocialAccount.objects.filter(user=user, uid=profile["id"]).exists())
        self.assertTrue(user.emailaddress_set.filter(verified=True).exists())
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(UserSession.objects.count(), 0)
        response = self.client.post(AUTH + "google/complete/", {})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["user"]["id"], user.pk)

    def test_google_does_not_link_existing_password_account_by_email(self):
        params, _ = self.google_start()
        profile = {"id": "new-provider-uid", "email": self.user.email, "verified_email": True}
        with patch("users.google_auth.OAuth2Client.get_access_token", return_value={"access_token": "provider-token"}), patch("users.google_auth.GoogleOAuth2Adapter._fetch_user_info", return_value=profile):
            self.client.get(AUTH + "google/callback/", {"state": params["state"][0], "code": "test-code"})
        response = self.client.post(AUTH + "google/complete/", {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["message"])
        self.assertFalse(SocialAccount.objects.exists())

    def test_two_factor_setup_cannot_delete_confirmed_device(self):
        response = self.login()
        device = TOTPDevice.objects.create(user=self.user, confirmed=True)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.post("/api/v1/users/2fa/create/", {}).status_code, 400)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())

    def test_profile_cannot_toggle_two_factor_flag(self):
        response = self.login()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.client.patch("/api/v1/users/profile/", {"is_2fa_enabled": True}, format="json")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)

    def test_registration_returns_tracked_cookie_session(self):
        response = self.client.post(AUTH + "registration/", {
            "username": "new-account", "email": "new@example.com", "first_name": "New", "last_name": "User",
            "password1": PASSWORD, "password2": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("refresh", response.data)
        self.assertTrue(UserSession.objects.filter(user_id=response.data["user"]["id"]).exists())

    def test_csrf_required_for_login_and_refresh(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post(AUTH + "login/", {"username": self.user.username, "password": PASSWORD}).status_code, 403)
        csrf = client.get(AUTH + "csrf/").data["csrf_token"]
        response = client.post(AUTH + "login/", {"username": self.user.username, "password": PASSWORD}, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(client.post(AUTH + "token/refresh/", {}).status_code, 403)
        self.assertEqual(client.post(AUTH + "token/refresh/", {}, HTTP_X_CSRFTOKEN=response.data["csrf_token"]).status_code, 200)

    def test_cross_user_revocation_returns_not_found(self):
        response = self.login()
        other_user = get_user_model().objects.create_user(username="second", email="second@example.com", password=PASSWORD)
        session = UserSession.objects.create(user=other_user, expires_at=timezone.now() + timedelta(days=1), refresh_jti="other")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.delete(AUTH + f"sessions/{session.pk}/").status_code, 404)
        self.assertTrue(UserSession.objects.filter(pk=session.pk).exists())

    def test_revocation_is_broadcast_only_after_commit(self):
        self.login()
        session = UserSession.objects.get()
        with patch("users.sessions._notify_revocation") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(AUTH + f"sessions/{session.pk}/")
                self.assertEqual(response.status_code, 200)
                notify.assert_not_called()
            notify.assert_called_once_with([session.session_id])

    def test_password_reset_ends_all_sessions_and_token_cannot_be_reused(self):
        from allauth.account.forms import default_token_generator
        from allauth.account.utils import user_pk_to_url_str
        self.login()
        self.login(APIClient())
        self.user.refresh_from_db()
        payload = {
            "uid": user_pk_to_url_str(self.user), "token": default_token_generator.make_token(self.user),
            "new_password1": "Password-Reset-2026!", "new_password2": "Password-Reset-2026!",
        }
        response = self.client.post(AUTH + "password/reset/confirm/", payload)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(UserSession.objects.count(), 0)
        self.assertEqual(self.client.post(AUTH + "password/reset/confirm/", payload).status_code, 400)

    def test_password_change_invalidates_pending_two_factor_challenge(self):
        TOTPDevice.objects.create(user=self.user, confirmed=True)
        raw_code, code_hash = BackupCode.generate_codes(1)[0]
        BackupCode.objects.create(user=self.user, code_hash=code_hash)
        challenge = self.login().data["login_token"]
        self.user.set_password("Changed-Password-2026!")
        self.user.save(update_fields=["password"])
        response = self.client.post(AUTH + "verify-2fa/", {"login_token": challenge, "otp_token": raw_code})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BackupCode.objects.get().is_used)

    def test_incorrect_backup_code_does_not_consume_challenge(self):
        TOTPDevice.objects.create(user=self.user, confirmed=True)
        raw_code, code_hash = BackupCode.generate_codes(1)[0]
        BackupCode.objects.create(user=self.user, code_hash=code_hash)
        challenge = self.login().data["login_token"]
        payload = {"login_token": challenge, "otp_token": "invalid"}
        self.assertEqual(self.client.post(AUTH + "verify-2fa/", payload).status_code, 400)
        payload["otp_token"] = raw_code
        self.assertEqual(self.client.post(AUTH + "verify-2fa/", payload).status_code, 200)

    def test_forwarded_ip_cannot_spoof_session_metadata(self):
        response = self.client.post(AUTH + "login/", {"username": self.user.username, "password": PASSWORD}, HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserSession.objects.get().ip_address, "127.0.0.1")

    def test_cleanup_removes_only_expired_sessions_and_tokens(self):
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        from .tasks import cleanup_expired_sessions
        self.login()
        expired = UserSession.objects.get()
        self.login(APIClient())
        UserSession.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(days=1))
        OutstandingToken.objects.filter(jti=expired.refresh_jti).update(expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(cleanup_expired_sessions(), 1)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(OutstandingToken.objects.count(), 1)

    def test_websocket_middleware_rejects_revoked_sessions(self):
        from backend.middleware.jwt_auth import JWTAuthMiddleware
        response = self.login()
        captured = []
        async def app(scope, receive, send):
            captured.append(scope["user"].is_authenticated)
        scope = {"type": "websocket", "headers": [(b"cookie", ("quantnest-auth=" + response.data["access"]).encode())]}
        async_to_sync(JWTAuthMiddleware(app))(scope, None, None)
        self.assertEqual(captured, [True])
        UserSession.objects.all().delete()
        async_to_sync(JWTAuthMiddleware(app))(scope, None, None)
        self.assertEqual(captured, [True, False])

    def test_websocket_middleware_rejects_inactive_users(self):
        from backend.middleware.jwt_auth import JWTAuthMiddleware
        response = self.login()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        captured = []
        async def app(scope, receive, send):
            captured.append(scope["user"].is_authenticated)
        scope = {"type": "websocket", "headers": [(b"cookie", ("quantnest-auth=" + response.data["access"]).encode())]}
        async_to_sync(JWTAuthMiddleware(app))(scope, None, None)
        self.assertEqual(captured, [False])

    def test_websocket_revocation_closes_existing_connection(self):
        from notifications.consumers import NotificationConsumer

        async def exercise():
            sid = str(uuid.uuid4())
            consumer = ApplicationCommunicator(NotificationConsumer.as_asgi(), {
                "type": "websocket", "user": self.user,
                "auth_session_id": sid, "auth_expires_at": time.time() + 60,
            })
            await consumer.send_input({"type": "websocket.connect"})
            self.assertEqual((await consumer.receive_output())["type"], "websocket.accept")
            await consumer.receive_output()  # Connection-established event.
            await get_channel_layer().group_send(f"auth_session_{sid}", {"type": "auth.session_revoked"})
            self.assertIn("auth.revoked", (await consumer.receive_output())["text"])
            self.assertEqual((await consumer.receive_output())["code"], 4401)
            await consumer.send_input({"type": "websocket.disconnect", "code": 4401})
            await consumer.wait()
        with patch("users.websocket.AuthSessionConsumerMixin._session_is_valid", new=AsyncMock(return_value=True)):
            async_to_sync(exercise)()
