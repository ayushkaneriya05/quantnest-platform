from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Locally bootstrap a staff TOTP device; store the displayed provisioning URI privately"
    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["username"], is_staff=True).first()
        if not user:
            raise CommandError("Select an existing staff account")
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            raise CommandError("A confirmed device already exists; use the reviewed recovery procedure")
        device = TOTPDevice.objects.create(user=user, name="operations", confirmed=True)
        user.is_2fa_enabled = True
        user.save(update_fields=["is_2fa_enabled"])
        self.stdout.write(device.config_url)
        self.stdout.write("Import this URI into your authenticator privately. It is a secret, not a support attachment.")
