from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Re-encrypt credential fields using the first configured key. Keep older keys until backup retention expires."
    def handle(self, **options):
        from brokers.models import BrokerCredential, BrokerSession
        from marketdata.models import MarketDataToken
        total = 0
        for model, names in ((BrokerCredential, ["api_secret"]),
                             (BrokerSession, ["access_token"]),
                             (MarketDataToken, ["access_token"])):
            ids = model.objects.order_by("pk").values_list("pk", flat=True).iterator(chunk_size=100)
            for pk in ids:
                with transaction.atomic():
                    row = model.objects.select_for_update().get(pk=pk)
                    row.save(update_fields=names)
                total += 1
        self.stdout.write(f"Re-encrypted {total} credential records. No secret values were printed.")
