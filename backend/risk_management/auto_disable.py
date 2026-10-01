from django.db import transaction

from common.enums import NotificationType
from notifications.services import NotificationService
from risk_management.evaluator import RiskEvaluator

class AutoDisableGate:
    """Evaluate session-scoped auto-disable rules after durable execution events."""

    @classmethod
    def evaluate(cls, session, stats, capital):
        rules = session.strategy.auto_disable_rules.filter(is_active=True)
        if not rules.exists():
            return None

        evaluation = RiskEvaluator(capital).evaluate_auto_disable_rules(rules, stats)
        if not evaluation.get("should_disable"):
            return None

        matches = evaluation.get("matches") or [{}]
        match = matches[0]
        message = match.get("message", "Strategy auto-disable triggered")

        with transaction.atomic():
            locked_session = (
                session.__class__.objects.select_for_update()
                .select_related("strategy", "user")
                .get(pk=session.pk)
            )
            paused_now = locked_session.status == "RUNNING"
            if paused_now:
                locked_session.status = "PAUSED"
                locked_session.error_message = message
                locked_session.save(update_fields=["status", "error_message", "updated_at"])

                module = {
                    "live_trading": "live",
                    "paper_trading": "paper",
                }.get(locked_session._meta.app_label, locked_session._meta.app_label)
                strategy = locked_session.strategy
                match_details = [
                    {
                        "rule_id": str(item["rule_id"]) if item.get("rule_id") is not None else None,
                        "rule_name": item.get("rule_name"),
                        "trigger_type": item.get("trigger_type"),
                        "actual_value": item.get("actual_value"),
                        "threshold": item.get("threshold"),
                    }
                    for item in matches
                ]
                NotificationService.notify(
                    user=locked_session.user,
                    type=NotificationType.WARNING,
                    title=f"{module.title()} strategy auto-paused: {strategy.name}",
                    message=message,
                    data={
                        "module": module,
                        "session_id": str(locked_session.pk),
                        "strategy_id": str(strategy.pk),
                        "strategy_name": strategy.name,
                        "matched_rules": match_details,
                    },
                    dedupe_key=f"auto-disable:{module}:{locked_session.pk}:{locked_session.updated_at.isoformat()}",
                )

            session.status = locked_session.status
            session.error_message = locked_session.error_message

        match["paused_now"] = paused_now

        return match
