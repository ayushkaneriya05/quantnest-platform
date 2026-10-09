"""Google authorization-code redirects finish through the shared session service."""
import base64
import hashlib
import json
import logging
import secrets

from allauth.account import app_settings as account_settings
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from dj_rest_auth.app_settings import api_settings as auth_settings
from requests import RequestException
from rest_framework.exceptions import APIException, AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.utils import get_md5_hash_password

from backend.middleware.api_responses import error_envelope
from .auth_views import AuthActionMixin, LoginThrottle, login_response

logger = logging.getLogger(__name__)
STATE_COOKIE = "quantnest-google-state"
RESULT_COOKIE = "quantnest-google-result"
FLOW_SECONDS = 300


def _callback_url():
    return settings.BACKEND_URL.rstrip("/") + reverse("google_oauth_callback")


def _cookie_path():
    return reverse("google_oauth_start").removesuffix("start/")


def _set_cookie(response, name, payload):
    response.set_signed_cookie(
        name, json.dumps(payload), salt=name, max_age=FLOW_SECONDS,
        httponly=True, secure=auth_settings.JWT_AUTH_SECURE, samesite="Lax",
        domain=auth_settings.JWT_AUTH_COOKIE_DOMAIN, path=_cookie_path(),
    )
    response["Cache-Control"] = "no-store"


def _read_cookie(request, name):
    try:
        return json.loads(request.get_signed_cookie(name, salt=name, max_age=FLOW_SECONDS))
    except (KeyError, signing.BadSignature, ValueError):
        raise ValidationError("Google sign-in has expired or is invalid. Please start again.")


def _use_once(payload):
    if not cache.add(f"google_oauth_used_{payload['nonce']}", True, timeout=FLOW_SECONDS):
        raise ValidationError("This Google sign-in has already been used. Please start again.")


def _client(request, adapter, app):
    return OAuth2Client(
        request, app.client_id, app.secret, adapter.access_token_method,
        adapter.access_token_url, _callback_url(), scope_delimiter=adapter.scope_delimiter,
        headers=adapter.headers, basic_auth=adapter.basic_auth,
    )


def _google_user(request, code, verifier):
    adapter = GoogleOAuth2Adapter(request)
    app = adapter.get_provider().app
    tokens = _client(request, adapter, app).get_access_token(code, pkce_code_verifier=verifier)
    adapter.did_fetch_access_token = True
    token = adapter.parse_token(tokens)
    token.app = app
    social_login = adapter.complete_login(request, app, token, response=tokens)
    social_login.token = token
    social_login.lookup()
    if not social_login.is_existing:
        social_adapter = get_adapter(request)
        if not social_adapter.is_open_for_signup(request, social_login):
            raise ValidationError("New account registration is currently closed.")
        if not social_login.user.email or not any(email.verified for email in social_login.email_addresses):
            raise ValidationError("Google must provide a verified email address to sign in.")
        if account_settings.UNIQUE_EMAIL and get_user_model().objects.filter(email__iexact=social_login.user.email).exists():
            raise ValidationError("An account with this email already exists. Sign in with your password.")
        # Save Google's account and verified email without creating a Django login session.
        with transaction.atomic():
            social_adapter.save_user(request, social_login)
    return social_login.user


class GoogleStartView(AuthActionMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        next_path = request.data.get("next", "/overview")
        if not isinstance(next_path, str) or not next_path.startswith("/") or not url_has_allowed_host_and_scheme(next_path, allowed_hosts=set()):
            raise ValidationError("The return page must be a local QuantNest path.")
        adapter = GoogleOAuth2Adapter(request._request)
        try:
            provider = adapter.get_provider()
        except ObjectDoesNotExist:
            raise ValidationError("Google sign-in is not configured. Please use your username and password.")
        if not provider.app.client_id or not provider.app.secret:
            raise ValidationError("Google sign-in requires a client ID and secret in the backend Google SocialApp.")
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        client = _client(request._request, adapter, provider.app)
        client.state = nonce
        authorization_url = client.get_redirect_url(adapter.authorize_url, ["openid", *provider.get_scope()], {
            "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account",
        })
        response = Response({"authorization_url": authorization_url})
        _set_cookie(response, STATE_COOKIE, {"nonce": nonce, "verifier": verifier, "next": next_path})
        response.delete_cookie(RESULT_COOKIE, path=_cookie_path(), domain=auth_settings.JWT_AUTH_COOKIE_DOMAIN)
        return response


class GoogleCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        result = {"nonce": secrets.token_urlsafe(32), "next": "/overview"}
        try:
            flow = _read_cookie(request, STATE_COOKIE)
            if not constant_time_compare(flow["nonce"], request.query_params.get("state", "")):
                raise ValidationError("Google sign-in could not be verified. Please start again.")
            _use_once(flow)
            result["next"] = flow["next"]
            if request.query_params.get("error"):
                raise ValidationError("Google sign-in was cancelled or denied. Please try again.")
            code = request.query_params.get("code")
            if not code:
                raise ValidationError("Google did not return an authorization code. Please try again.")
            user = _google_user(request._request, code, flow["verifier"])
            if not user.is_active:
                raise AuthenticationFailed("This account is inactive.")
            result.update(user_id=user.pk, password_hash=get_md5_hash_password(user.password))
        except APIException as error:
            result["error"] = error_envelope({"detail": error.detail}, error.status_code)["message"]
        except (OAuth2Error, RequestException, IntegrityError):
            logger.warning("Google OAuth exchange failed; no session was issued")
            result["error"] = "Could not complete Google sign-in. Please try again."
        except Exception as error:
            # OAuth exceptions can contain provider tokens; never log their payloads.
            logger.error("Google OAuth callback failed (%s)", type(error).__name__)
            result["error"] = "Could not complete Google sign-in. Please try again."
        response = HttpResponseRedirect(settings.FRONTEND_URL.rstrip("/") + "/google-callback")
        response["Referrer-Policy"] = "no-referrer"
        _set_cookie(response, RESULT_COOKIE, result)
        response.delete_cookie(STATE_COOKIE, path=_cookie_path(), domain=auth_settings.JWT_AUTH_COOKIE_DOMAIN)
        return response


class GoogleCompleteView(AuthActionMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        result = _read_cookie(request, RESULT_COOKIE)
        _use_once(result)
        if result.get("error"):
            raise ValidationError(result["error"])
        user = get_user_model().objects.filter(pk=result["user_id"], is_active=True).first()
        if user is None or result["password_hash"] != get_md5_hash_password(user.password):
            raise AuthenticationFailed("Your account has changed. Please sign in again.")
        response = login_response(user, request)
        response.data["next"] = result["next"]
        response.delete_cookie(RESULT_COOKIE, path=_cookie_path(), domain=auth_settings.JWT_AUTH_COOKIE_DOMAIN)
        return response
