import hmac
import hashlib
import httpx
from urllib.parse import quote
from django.conf import settings
from django.core import signing
from commercial.usage import reject_request


def require_form_verification(token, request, action):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development" and settings.DEBUG:
        return
    if not settings.TURNSTILE_SECRET_KEY or not token:
        reject_request("challenge_required", "Complete the form verification before sending.")
    try:
        result = httpx.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token}, timeout=8).json()
    except (httpx.HTTPError, ValueError):
        reject_request("challenge_unavailable", "Verification is temporarily unavailable. Please retry.")
    if not result.get("success") or result.get("hostname") not in settings.TURNSTILE_HOSTNAMES or result.get("action") != action:
        reject_request("challenge_failed", "Form verification failed. Please complete it again.")


def request_brevo(method, path, payload=None, *, allow_missing=False):
    if not settings.BREVO_API_KEY:
        raise RuntimeError("Brevo API is not configured")
    response = httpx.request(method, "https://api.brevo.com/v3/" + path, json=payload,
        headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"}, timeout=10)
    if allow_missing and response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json() if response.content else {}


def withdraw_newsletter(email):
    request_brevo("PUT", "contacts/" + quote(email, safe=""), {"emailBlacklisted": True}, allow_missing=True)


def sync_newsletter_consent(consent_id):
    from .models import Consent
    consent = Consent.objects.get(pk=consent_id)
    if consent.state == "withdrawn":
        withdraw_newsletter(consent.email)
        return
    if not settings.BREVO_DOI_TEMPLATE_ID or not settings.BREVO_NEWSLETTER_LIST_ID:
        raise RuntimeError("Brevo double opt-in template/list is not configured")
    token = signing.dumps({"consent_id": consent.pk, "requested_at": consent.requested_at.isoformat()}, salt="newsletter-confirm")
    request_brevo("POST", "contacts/doubleOptinConfirmation", {"email": consent.email,
        "includeListIds": [settings.BREVO_NEWSLETTER_LIST_ID], "templateId": settings.BREVO_DOI_TEMPLATE_ID,
        "redirectionUrl": settings.FRONTEND_URL.rstrip("/") + "/newsletter/confirmed/?token=" + token})


def is_brevo_webhook_authenticated(request):
    expected = settings.BREVO_WEBHOOK_TOKEN
    return bool(expected and hmac.compare_digest(request.headers.get("Authorization", "").encode(), ("Bearer " + expected).encode()))


def get_ticket_reply_address(ticket):
    if not settings.BREVO_INBOUND_DOMAIN:
        return ""
    mac = hmac.new(settings.SECRET_KEY.encode(), ("support-reply:" + ticket.id.hex).encode(), hashlib.sha256).hexdigest()[:24]
    return f"reply+{ticket.id.hex}.{mac}@{settings.BREVO_INBOUND_DOMAIN}"


def get_ticket_from_reply_address(address):
    import uuid
    from .models import Ticket
    if not isinstance(address, str):
        return None
    local, _, domain = address.partition("@")
    if domain.lower() != settings.BREVO_INBOUND_DOMAIN.lower() or not local.startswith("reply+"):
        return None
    try:
        identity, _ = local[6:].split(".")
        ticket = Ticket.objects.get(pk=uuid.UUID(hex=identity))
    except (ValueError, Ticket.DoesNotExist):
        return None
    return ticket if hmac.compare_digest(address.lower().encode(), get_ticket_reply_address(ticket).lower().encode()) else None
