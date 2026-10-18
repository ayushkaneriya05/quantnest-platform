"""Administrator authorization of the shared FYERS market-data connection."""
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core import signing
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from fyers_apiv3 import fyersModel
from redis.exceptions import RedisError
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser

from backend.middleware.api_responses import api_json_error
from users.authentication import SafeJWTAuthentication
from .utils import _get_token_row, _get_today_eod

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
        if request.method == "GET" and _origin(f"{request.scheme}://{host}") != _origin(callback):
            return _response(redirect(origin + reverse("fyers_login")))
    except ValueError as error:
        return _response(api_json_error(str(error), status_code=503, code="fyers_configuration"))
    response = _authorize_source(request)
    if response.status_code in {401, 403} and "text/html" in request.headers.get("Accept", ""):
        response = redirect_to_login(reverse("fyers_login"), login_url=origin + reverse("admin:login"))
    return _response(response)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, SafeJWTAuthentication])
@permission_classes([IsAdminUser])
def _authorize_source(request):
    if not settings.FYERS_CLIENT_ID or not settings.FYERS_SECRET:
        return api_json_error("Configure FYERS_CLIENT_ID and FYERS_SECRET before connecting market data.", status_code=503, code="fyers_configuration")
    callback = _callback_uri()
    state = signing.dumps({"user_id": request.user.pk, "nonce": secrets.token_urlsafe(24), "callback": callback}, salt="fyers-source-oauth")
    session = fyersModel.SessionModel(
        client_id=settings.FYERS_CLIENT_ID, secret_key=settings.FYERS_SECRET,
        redirect_uri=callback, response_type="code", grant_type="authorization_code",
    )
    url = urlsplit(session.generate_authcode())
    query = dict(parse_qsl(url.query))
    query["state"] = state
    response = redirect(urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), url.fragment)))
    response.set_cookie(STATE_COOKIE, state, max_age=FLOW_SECONDS, secure=not settings.DEBUG,
        httponly=True, samesite="Lax", path=reverse("fyers_callback").removesuffix("callback/"))
    return response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def fyers_callback(request):
    # This browser redirect is authenticated by the signed, browser-bound state,
    # independent of a workspace JWT expiring while the administrator signs in.
    def error(message, code, status_code=403, *, clear_state=False):
        return _response(api_json_error(message, status_code=status_code, code=code,
            details={"login_url": reverse("fyers_login")}), clear_state=clear_state)

    state = request.query_params.get("state", "")
    cookie = request.COOKIES.get(STATE_COOKIE, "")
    if not state:
        return error("FYERS did not return the sign-in state. Start a new market-data sign-in.", "fyers_state_missing")
    if not cookie:
        return error("The sign-in verification cookie is missing or expired. Start again using the configured callback address and the same browser.", "fyers_cookie_missing")
    if not hmac.compare_digest(state.encode(), cookie.encode()):
        return error("A different sign-in replaced this request. Finish the most recent sign-in or start again.", "fyers_state_mismatch")
    try:
        payload = signing.loads(state, salt="fyers-source-oauth", max_age=FLOW_SECONDS)
        if (not isinstance(payload, dict) or not isinstance(payload.get("nonce"), str)
                or not payload["nonce"] or payload.get("callback") != _callback_uri()):
            raise signing.BadSignature()
        if not get_user_model().objects.filter(pk=payload.get("user_id"), is_active=True, is_staff=True).exists():
            raise signing.BadSignature()
    except signing.SignatureExpired:
        return error("The ten-minute sign-in window expired. Start a new market-data sign-in.", "fyers_state_expired", clear_state=True)
    except (signing.BadSignature, ValueError, TypeError):
        return error("This sign-in cannot be verified. Start a new market-data sign-in.", "fyers_state_invalid", clear_state=True)
    if not settings.FYERS_CLIENT_ID or not settings.FYERS_SECRET:
        return error("Market-data authorization is not configured on the server.", "fyers_configuration", 503)
    try:
        unused = cache.add("fyers-source-oauth-used:" + payload["nonce"], True, timeout=FLOW_SECONDS)
    except (RedisError, OSError):
        logger.error("FYERS source authorization storage is unavailable")
        return error("Sign-in verification is temporarily unavailable. Try again shortly.", "fyers_oauth_unavailable", 503)
    if not unused:
        return error("This sign-in has already been used. Start a new market-data sign-in.", "fyers_state_used", clear_state=True)
    auth_code = request.query_params.get("auth_code") or request.query_params.get("authCode")
    if not auth_code:
        return error("FYERS sign-in was cancelled or did not return an authorization code. Start again and approve access.", "fyers_code_missing", 400, clear_state=True)
    try:
        session = fyersModel.SessionModel(
            client_id=settings.FYERS_CLIENT_ID, secret_key=settings.FYERS_SECRET,
            redirect_uri=payload["callback"], response_type="code", grant_type="authorization_code",
        )
        session.set_token(auth_code)
        token = session.generate_token()
    except Exception as exception:
        logger.error("FYERS source token exchange failed (%s)", type(exception).__name__)
        return error("Could not complete FYERS sign-in. Start a new sign-in and try again.", "fyers_exchange_failed", 502, clear_state=True)
    access_token = (token.get("access_token") or token.get("accessToken")) if isinstance(token, dict) else None
    if not isinstance(access_token, str) or not access_token:
        return error("FYERS did not authorize market-data access. Start a new sign-in and approve access.", "fyers_authorization_failed", 400, clear_state=True)
    token_row = _get_token_row()
    token_row.access_token = access_token
    token_row.is_active = True
    token_row.token_type = token.get("token_type") or token_row.token_type
    token_row.expires_at = _get_today_eod()
    try:
        expires_in = int(token.get("expires_in") or token.get("expiresIn") or 0)
        if expires_in > 0:
            token_row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    except (TypeError, ValueError, OverflowError):
        pass  # Providers without a usable duration retain the market-day expiry.
    token_row.save()
    response = JsonResponse({"status": "ok", "token_saved": True}) if (
        request.headers.get("Accept", "").startswith("application/json") or request.query_params.get("json")
    ) else redirect(settings.FRONTEND_URL)
    return _response(response, clear_state=True)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, SafeJWTAuthentication])
@permission_classes([IsAdminUser])
def fyers_token_status(request):
    token = _get_token_row()
    return _response(JsonResponse({"has_token": bool(token.access_token), "is_valid": token.is_valid(),
        "expires_at": token.expires_at, "updated_at": token.updated_at}))
