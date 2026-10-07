from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .auto_disable import AutoDisableGate
from .policy import cooldown_elapsed


@shared_task(name="risk_management.check_and_reenable_strategies")
def check_and_reenable_strategies():
    """Resume only recorded risk pauses, using the rules that were deployed."""
    from paper_trading.models import PaperTradingSession
    from paper_trading.services import PaperExecutionService
    from live_trading.models import TradingSession
    from live_trading.services import LiveExecutionService

    count = 0
    for model, scope, service in ((PaperTradingSession, "paper", PaperExecutionService),
                                  (TradingSession, "live", LiveExecutionService)):
        ids = model.objects.filter(status="PAUSED").values_list("pk", flat=True)
        for session_id in ids:
            with transaction.atomic():
                session = model.objects.select_for_update(of=("self",)).select_related(
                    "strategy", "allocation__deployed_version", "user").get(pk=session_id)
                if session.status != "PAUSED" or not cooldown_elapsed(session.auto_disable_state, timezone.now()):
                    continue
                if not session.allocation or session.auto_disable_state.get("version_id") != session.allocation.deployed_version_id:
                    continue
                config = AutoDisableGate.configuration(session)
                matches = session.auto_disable_state.get("matches", [])
                if not matches or any(item["rule_index"] >= len(config["auto_disable_rules"]) or not config["auto_disable_rules"][item["rule_index"]].get("auto_reenable", False) for item in matches):
                    continue
                if session.strategy.status != "ACTIVE" or not getattr(session.strategy, f"{scope}_trading_enabled"):
                    continue
                AutoDisableGate.release(session)
                session.status = "RUNNING"
                session.error_message = ""
                session.save(update_fields=["status", "error_message", "auto_disable_state", "updated_at"])
                transaction.on_commit(lambda session=session, service=service, scope=scope: service._publish_execution_event("SESSION_START", session, scope))
                count += 1
    return {"reenabled": count}
