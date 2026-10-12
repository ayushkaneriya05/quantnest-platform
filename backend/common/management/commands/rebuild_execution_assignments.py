"""One-shot topology maintenance, run only with execution services stopped."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Rebuild indexed execution partitions after a coordinated topology change."

    def handle(self, *args, **options):
        from core.redis import runtime_redis
        from core.assignments import synchronize
        from common.models import RuntimeAssignment
        from live_trading.models import TradingSession
        from paper_trading.models import PaperTradingSession
        from django.db import transaction
        if any(runtime_redis().scan_iter(match="quantnest:lease:execution:*", count=100)):
            raise CommandError("Stop execution services before rebuilding assignments.")
        with transaction.atomic():
            RuntimeAssignment.objects.all().delete()
            for scope, model in (("live", TradingSession), ("paper", PaperTradingSession)):
                for identity in model.objects.exclude(status="STOPPED").values_list("pk", flat=True).iterator():
                    synchronize(scope, identity)
        self.stdout.write(self.style.SUCCESS("Execution assignments rebuilt."))
