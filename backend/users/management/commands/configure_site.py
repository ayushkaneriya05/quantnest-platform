"""Configure Django's selected Site from the deployment's existing public identity."""
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Create/update the configured Django Site for email links and social sign-in."

    def handle(self, *args, **options):
        origin = urlparse(settings.FRONTEND_URL)
        if origin.scheme not in {"http", "https"} or not origin.netloc or origin.username or origin.password:
            raise CommandError("Configure FRONTEND_URL as the browser's HTTP(S) origin")
        with transaction.atomic():
            Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": origin.netloc, "name": settings.QUANTNEST_LEGAL_NAME})
            with connection.cursor() as cursor:
                for statement in connection.ops.sequence_reset_sql(no_style(), [Site]):
                    cursor.execute(statement)
        Site.objects.clear_cache()
        self.stdout.write(f"Configured Django Site {settings.SITE_ID}: {origin.netloc}")
