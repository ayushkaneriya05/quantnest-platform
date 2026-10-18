"""One-off provisioning, not a persistent execution process."""
import hashlib
import secrets
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from installations.models import Installation, PrivateContract


class Command(BaseCommand):
    help = "Provision an approved Private contract and display its activation token once"
    def add_arguments(self, parser):
        parser.add_argument("--contract", type=int, required=True)
    def handle(self, *args, **options):
        if settings.QUANTNEST_DEPLOYMENT_MODE == "private":
            raise CommandError("Provision installations on the central QuantNest service, not on a customer server.")
        with transaction.atomic():
            contract = PrivateContract.objects.select_for_update().filter(pk=options["contract"], approved=True).first()
            if not contract:
                raise CommandError("Select an approved Private contract")
            try:
                contract.full_clean()
            except ValidationError as exc:
                raise CommandError("Complete the approved contract: " + "; ".join(exc.messages)) from None
            token = secrets.token_urlsafe(48)
            installation = Installation.objects.create(contract=contract, activation_hash=hashlib.sha256(token.encode()).hexdigest())
        self.stdout.write(f"LICENSE_INSTALLATION_ID={installation.pk}")
        self.stdout.write(f"LICENSE_ACTIVATION_TOKEN={token}")
        self.stdout.write("Store the activation token securely. Only its hash is stored centrally.")
