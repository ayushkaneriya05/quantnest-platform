import httpx
from django.conf import settings
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
