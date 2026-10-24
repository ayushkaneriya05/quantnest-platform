"""Administrator authorization of the shared FYERS market-data connection."""
import hmac
import logging
import secrets
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core import signing
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET
from redis.exceptions import RedisError
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAdminUser

from backend.middleware.api_responses import api_json_error
from brokers.fyers import FyersAuth
from users.authentication import SafeJWTAuthentication
from .models import MarketDataToken

logger = logging.getLogger(__name__)
STATE_COOKIE = "quantnest-source-oauth"
FLOW_SECONDS = 600


def _callback_uri():
    uri = settings.FYERS_REDIRECT_URI
    parts = urlsplit(uri)
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.path != reverse("fyers_callback")
            or (not settings.DEBUG and parts.scheme != "https")):
        raise ValueError("Configure FYERS_REDIRECT_URI as the exact QuantNest callback URL; production requires HTTPS.")
    return uri


def _origin(uri):
    parts = urlsplit(uri)
    return parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)


def _response(response, *, clear_state=False):
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    if clear_state:
        response.delete_cookie(STATE_COOKIE, path=reverse("fyers_callback").removesuffix("callback/"), samesite="Lax")
    return response


@require_GET
def fyers_login(request):
    """Start on the callback origin so the browser can return its verification cookie."""
    try:
        callback = _callback_uri()
        parts = urlsplit(callback)
        origin = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
        host = request.get_host()
        if settings.QUANTNEST_DEPLOYMENT_MODE == "public":
            # TrustedIngressMiddleware verifies the gateway before this view.
            # Its browser host differs from the API origin behind Cloudflare.
            host = request.headers.get("X-Forwarded-Host") or host
        if _origin(f"{request.scheme}://{host}") != _origin(callback):
            return _response(redirect(origin + reverse("fyers_login")))
        response = _authorize_source(request, callback)
    except ValueError as error:
        return _response(api_json_error(str(error), status_code=503, code="fyers_configuration"))
    if response.status_code in {401, 403} and "text/html" in request.headers.get("Accept", ""):
        response = redirect_to_login(reverse("fyers_login"), login_url=origin + reverse("admin:login"))
    return _response(response)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, SafeJWTAuthentication])
@permission_classes([IsAdminUser])
def _authorize_source(request, callback: str):
    auth = FyersAuth(settings.FYERS_CLIENT_ID, settings.FYERS_SECRET, callback)
    state = signing.dumps({"user_id": request.user.pk, "nonce": secrets.token_urlsafe(24), "callback": callback}, salt="fyers-source-oauth")
    response = redirect(auth.authorization_url(state))
    response.set_cookie(STATE_COOKIE, state, max_age=FLOW_SECONDS, secure=urlsplit(callback).scheme == "https",
        httponly=True, samesite="Lax", path=reverse("fyers_callback").removesuffix("callback/"))
    return response


@require_GET
def fyers_callback(request):
    # This browser redirect is authenticated by the signed, browser-bound state,
    # independent of a workspace JWT expiring while the administrator signs in.
    def error(message, code, status_code=403, *, clear_state=False):
        return _response(api_json_error(message, status_code=status_code, code=code,
            details={"login_url": reverse("fyers_login")}), clear_state=clear_state)

    state = request.GET.get("state", "")
    cookie = request.COOKIES.get(STATE_COOKIE, "")
    if not state:
        return error("FYERS did not return the sign-in state. Start a new market-data sign-in.", "fyers_state_missing")
    if not cookie:
        return error("The sign-in verification cookie is missing or expired. Start again using the configured callback address and the same browser.", "fyers_cookie_missing")
    if not hmac.compare_digest(state.encode(), cookie.encode()):
        return error("A different sign-in replaced this request. Finish the most recent sign-in or start again.", "fyers_state_mismatch")
    try:
        auth = FyersAuth(settings.FYERS_CLIENT_ID, settings.FYERS_SECRET, _callback_uri())
    except ValueError:
        return error("Check the FYERS market-data app credentials and callback URL on the server.", "fyers_configuration", 503)
    try:
        payload = signing.loads(state, salt="fyers-source-oauth", max_age=FLOW_SECONDS)
        if (not isinstance(payload, dict) or not isinstance(payload.get("nonce"), str)
                or not payload["nonce"] or payload.get("callback") != auth.redirect_uri):
            raise signing.BadSignature()
        if not get_user_model().objects.filter(pk=payload.get("user_id"), is_active=True, is_staff=True).exists():
            raise signing.BadSignature()
    except signing.SignatureExpired:
        return error("The ten-minute sign-in window expired. Start a new market-data sign-in.", "fyers_state_expired", clear_state=True)
    except (signing.BadSignature, ValueError, TypeError):
        return error("This sign-in cannot be verified. Start a new market-data sign-in.", "fyers_state_invalid", clear_state=True)
    try:
        unused = cache.add("fyers-source-oauth-used:" + payload["nonce"], True, timeout=FLOW_SECONDS)
    except (RedisError, OSError):
        logger.error("FYERS source authorization storage is unavailable")
        return error("Sign-in verification is temporarily unavailable. Try again shortly.", "fyers_oauth_unavailable", 503)
    if not unused:
        return error("This sign-in has already been used. Start a new market-data sign-in.", "fyers_state_used", clear_state=True)
    auth_code = request.GET.get("auth_code")
    if not auth_code:
        return error("FYERS sign-in was cancelled or did not return an authorization code. Start again and approve access.", "fyers_code_missing", 400, clear_state=True)
    try:
        token = auth.exchange_code(auth_code)
    except Exception as exception:
        logger.error("FYERS source token exchange failed (%s)", type(exception).__name__)
        return error("Could not complete FYERS sign-in. Start a new sign-in and try again.", "fyers_exchange_failed", 502, clear_state=True)
    MarketDataToken.objects.update_or_create(pk=1, defaults={
        "access_token": token["access_token"], "expires_at": token["expires_at"], "is_active": True,
    })
    response = JsonResponse({"status": "ok", "token_saved": True}) if (
        request.headers.get("Accept", "").startswith("application/json") or request.GET.get("json")
    ) else redirect(settings.FRONTEND_URL)
    return _response(response, clear_state=True)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, SafeJWTAuthentication])
@permission_classes([IsAdminUser])
def fyers_token_status(request):
    token = MarketDataToken.objects.filter(pk=1).first()
    return _response(JsonResponse({"has_token": bool(token and token.access_token), "is_valid": bool(token and token.is_valid()),
        "expires_at": token.expires_at if token else None, "updated_at": token.updated_at if token else None}))
