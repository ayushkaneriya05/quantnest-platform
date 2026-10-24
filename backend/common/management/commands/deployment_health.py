"""Deployment readiness and bounded operational metrics."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from execution.models import Command as ExecutionCommand
from backend.health import get_readiness_status


class Command(BaseCommand):
    help = "Check deployment readiness or print content-free operational metrics."

    def add_arguments(self, parser):
        parser.add_argument("--require-mode", choices=["development", "public", "private"])
        parser.add_argument("--workers", action="store_true", help="Require active execution workers.")
        parser.add_argument("--metrics", action="store_true", help="Print metrics for the deployment monitor.")

    def handle(self, **options):
        if options["require_mode"] and settings.QUANTNEST_DEPLOYMENT_MODE != options["require_mode"]:
            raise CommandError("The configured deployment mode does not match this installation")
        checks = get_readiness_status(workers=options["workers"] or options["metrics"])
        if options["metrics"]:
            self.stdout.write(json.dumps(self.get_metrics(checks)))
            return
        if not all(checks.values()):
            raise CommandError("Deployment dependency checks failed")
        self.stdout.write(json.dumps(checks))

    @staticmethod
    def get_metrics(checks):
        oldest = ExecutionCommand.objects.filter(applied_at__isnull=True).order_by("id").values_list("created_at", flat=True).first()
        metrics = {
            "database_ok": int(checks["database"]),
            "execution_workers_ok": int(checks.get("execution_workers", False)),
            "execution_command_oldest_seconds": max(0, (timezone.now() - oldest).total_seconds()) if oldest else 0,
        }
        from marketdata.live_feed import LiveMarketDataRegistry
        state = LiveMarketDataRegistry.get_state()
        metrics.update({
            "market_data_connected": int(state.get("connected", False)),
            "market_data_subscribed_symbols": len(state.get("subscribed", ())),
            "market_data_rejected_symbols": len(state.get("rejected", {})),
            "market_data_history_pending_symbols": sum(
                bool(depths) and not LiveMarketDataRegistry.is_ready(symbol, depths, state)
                for symbol, depths in state.get("requirements", {}).items()),
        })
        return metrics
