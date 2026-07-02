from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom adapter to inject FRONTEND_URL into email template context."""

    def send_mail(self, template_prefix, email, context):
        context["frontend_url"] = settings.FRONTEND_URL
        super().send_mail(template_prefix, email, context)
