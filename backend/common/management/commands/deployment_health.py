import json
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check deployment database/runtime readiness without exposing identities or secrets."
    def add_arguments(self, parser):
        parser.add_argument("--require-mode", choices=["development", "public", "private"])
        parser.add_argument("--workers", action="store_true", help="Also require fresh execution worker heartbeats")
    def handle(self, **options):
        from django.conf import settings
        if options.get("require_mode") and settings.QUANTNEST_DEPLOYMENT_MODE != options["require_mode"]:
            raise CommandError("The configured deployment mode does not match this installation")
        from quantnest_runtime.health import get_readiness_status
        checks = get_readiness_status(workers=options["workers"])
        if not all(checks.values()):
            raise CommandError("Deployment dependency checks failed")
        self.stdout.write(json.dumps(checks))
