"""One revocable session per user and browser profile, shared by all login paths."""
import ipaddress
import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from dj_rest_auth.app_settings import api_settings as auth_settings
from dj_rest_auth.jwt_auth import set_jwt_cookies
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch, get_md5_hash_password

from .models import UserSession
from .tokens import CustomRefreshToken

logger = logging.getLogger(__name__)
DEVICE_COOKIE = "quantnest-device"


def token_session_id(token):
    try:
        return uuid.UUID(str(token.get("session_id")))
    except (ValueError, TypeError, AttributeError):
        raise AuthenticationFailed("Invalid session. Please sign in again.", code="session_revoked")


def _request_metadata(request):
    agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    browser = next((name for marker, name in (
        ("Edg", "Edge"), ("OPR", "Opera"), ("Chrome", "Chrome"),
        ("Firefox", "Firefox"), ("Safari", "Safari"),
    ) if marker in agent), "Unknown")
    os_name = next((name for marker, name in (
        ("Android", "Android"), ("iPhone", "iOS"), ("iPad", "iOS"),
        ("Windows", "Windows"), ("Macintosh", "macOS"), ("Linux", "Linux"),
    ) if marker in agent), "Unknown")
    device = "Tablet" if "iPad" in agent or "Tablet" in agent else "Mobile" if "Mobile" in agent else "Desktop"
    # REMOTE_ADDR is supplied by the server; do not trust arbitrary forwarded headers.
    try:
        ip = str(ipaddress.ip_address(request.META.get("REMOTE_ADDR", "")))
    except ValueError:
        ip = None
    return {"user_agent": agent, "browser": browser, "os": os_name, "device_type": device, "ip_address": ip}


def _blacklist_jtis(jtis):
    for token in OutstandingToken.objects.filter(jti__in=jtis):
        BlacklistedToken.objects.get_or_create(token=token)


def _notify_revocation(session_ids, event_type="auth.session_revoked"):
    layer = get_channel_layer()
    if layer is None:
        return
    for session_id in session_ids:
        try:
            async_to_sync(layer.group_send)(f"auth_session_{session_id}", {"type": event_type})
        except Exception:
            # Authentication is already revoked in the database even if delivery fails.
            logger.exception("Could not broadcast session revocation")


@transaction.atomic
def revoke_sessions(user, *, exclude_session_id=None, session_pk=None):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    sessions = UserSession.objects.filter(user=user)
    if exclude_session_id:
        sessions = sessions.exclude(session_id=exclude_session_id)
    if session_pk is not None:
        sessions = sessions.filter(pk=session_pk)
    records = list(sessions.values_list("session_id", "refresh_jti"))
    _blacklist_jtis([jti for _, jti in records])
    count = sessions.count()
    sessions.delete()
    if count:
        from audit.services import AuditService
        AuditService.log_action(user, "LOGOUT", user, actor_name=user.get_username(), reason=f"Ended {count} authorized browser session(s)")
    transaction.on_commit(lambda: _notify_revocation([sid for sid, _ in records]))
    return count


def refresh_session_connections(session_id):
    transaction.on_commit(lambda: _notify_revocation([session_id], "auth.credentials_changed"))


def _token_response(request, refresh, *, user=None, status=200):
    access = refresh.access_token
    data = {"access": str(access), "access_expiration": datetime_from_epoch(access["exp"]), "csrf_token": get_token(request)}
    if user is not None:
        from .serializers import UserProfileSerializer
        data["user"] = UserProfileSerializer(user, context={"request": request}).data
    response = Response(data, status=status)
    set_jwt_cookies(response, access, refresh)
    response["Cache-Control"] = "no-store"
    return response


@transaction.atomic
def issue_login_response(user, request, *, refresh=None, status=200):
    authenticated_password = user.password
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if not user.is_active or user.password != authenticated_password:
        raise AuthenticationFailed("Sign-in details have changed. Please sign in again.")
    try:
        device_id = uuid.UUID(request.COOKIES.get(DEVICE_COOKIE, ""))
    except (ValueError, TypeError):
        device_id = uuid.uuid4()
    now = timezone.now()
    UserSession.objects.filter(user=user, expires_at__lte=now).delete()
    session = UserSession.objects.filter(user=user, device_id=device_id).first()
    if session:
        _blacklist_jtis([session.refresh_jti])
    else:
        session = UserSession(user=user, device_id=device_id)
    refresh = refresh if refresh is not None else CustomRefreshToken.for_user(user)
    refresh["session_id"] = str(session.session_id)
    # for_user records the token before the session claim has been assigned.
    OutstandingToken.objects.filter(jti=refresh["jti"]).update(token=str(refresh))
    session.refresh_jti = refresh["jti"]
    session.expires_at = datetime_from_epoch(refresh["exp"])
    for field, value in _request_metadata(request).items():
        setattr(session, field, value)
    session.save()
    get_user_model().objects.filter(pk=user.pk).update(last_login=now)
    from audit.services import AuditService
    AuditService.log_action(user, "LOGIN", user, request=request, actor_name=user.get_username(), reason="Signed in successfully")
    rotate_token(request)
    response = _token_response(request, refresh, user=user, status=status)
    response.set_cookie(
        DEVICE_COOKIE, str(device_id), max_age=365 * 86400,
        httponly=True, secure=auth_settings.JWT_AUTH_SECURE,
        samesite=auth_settings.JWT_AUTH_SAMESITE, domain=auth_settings.JWT_AUTH_COOKIE_DOMAIN,
        path=auth_settings.JWT_AUTH_REFRESH_COOKIE_PATH,
    )
    return response


@transaction.atomic
def refresh_session(request, raw_token):
    # Verify signature, expiry and blacklist before reading any claims.
    refresh = CustomRefreshToken(raw_token)
    user = get_user_model().objects.select_for_update().filter(pk=refresh.get("user_id"), is_active=True).first()
    if user is None or refresh.get(jwt_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
        raise AuthenticationFailed("Your session has ended. Please sign in again.")
    session = UserSession.objects.select_for_update().filter(
        session_id=token_session_id(refresh), user=user, expires_at__gt=timezone.now(),
    ).first()
    if session is None or session.refresh_jti != refresh["jti"]:
        raise AuthenticationFailed("Your session has ended. Please sign in again.", code="session_revoked")
    refresh.blacklist()
    refresh.set_jti()
    refresh.set_exp()
    refresh.set_iat()
    refresh.outstand()
    session.refresh_jti = refresh["jti"]
    session.expires_at = datetime_from_epoch(refresh["exp"])
    session.save(update_fields=["refresh_jti", "expires_at", "last_activity"])
    return _token_response(request, refresh)
