from urllib.parse import urlparse
from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def check_deployment_security(app_configs, **kwargs):
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return [Error("Production must select public or private mode.", id="quantnest.E001")]
    checks = []
    required = {
        "quantnest.E002": (not settings.DEBUG, "DEBUG must be disabled."),
        "quantnest.E003": (len(settings.SECRET_KEY) >= 50, "Set a long random Django signing key."),
        "quantnest.E004": (len(settings.QUANTNEST_PROXY_TOKEN) >= 32, "Set a strong trusted ingress token."),
        "quantnest.E005": (bool(settings.CREDENTIAL_ENCRYPTION_KEYS), "Configure credential encryption keys before migrating."),
        "quantnest.E006": (urlparse(settings.FRONTEND_URL).scheme == "https", "The public frontend origin must use HTTPS."),
        "quantnest.E008": (not settings.BILLING_ENABLED or bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and settings.RAZORPAY_WEBHOOK_SECRET), "Enabled billing requires approved provider credentials and webhook verification."),
        "quantnest.E010": (settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql", "Production execution requires PostgreSQL."),
        "quantnest.E011": (settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend" or bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD and settings.DEFAULT_FROM_EMAIL), "Configure the Brevo SMTP login, SMTP key and verified sender."),
        "quantnest.E012": (len(settings.RESEARCH_SERVICE_TOKEN) >= 32, "Set a strong shared research service token."),
        "quantnest.E013": (settings.EMAIL_BACKEND not in {"django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.dummy.EmailBackend", "django.core.mail.backends.locmem.EmailBackend", "django.core.mail.backends.filebased.EmailBackend"}, "Production account mail needs a delivery transport; configure the Brevo SMTP backend."),
    }
    from cryptography.fernet import Fernet
    try:
        for key in settings.CREDENTIAL_ENCRYPTION_KEYS:
            Fernet(key.encode())
    except (ValueError, TypeError):
        checks.append(Error("Credential encryption keys are invalid.", id="quantnest.E007"))
    for identity, (passed, message) in required.items():
        if not passed:
            checks.append(Error(message, id=identity))
    return checks
