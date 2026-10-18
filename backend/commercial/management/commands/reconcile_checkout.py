from django.core.management.base import BaseCommand
from commercial.models import PaymentAttempt
from commercial.reconciliation import link_provider_checkout, reconcile_checkout_attempt


class Command(BaseCommand):
    help = "Verify and link a remotely created checkout after an uncertain request; never creates another mandate/order."
    def add_arguments(self, parser):
        parser.add_argument("attempt_id")
        parser.add_argument("provider_id")
    def handle(self, attempt_id, provider_id, **options):
        attempt = PaymentAttempt.objects.get(pk=attempt_id)
        attempt = link_provider_checkout(attempt, provider_id)
        reconcile_checkout_attempt(attempt)
        self.stdout.write("Provider resource verified and reconciled.")
