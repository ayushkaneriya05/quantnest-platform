import logging

from common.enums import AutoDisableTriggerType, NotificationType, Severity, ViolationAction, ViolationType
from risk_management.evaluator import RiskEvaluator
from risk_management.models import RiskViolation
from notifications.services import NotificationService

logger = logging.getLogger(__name__)


class AutoDisableGate:
    """Evaluate session-scoped auto-disable rules after durable execution events."""

    VIOLATION_TYPES = {
        AutoDisableTriggerType.CONSECUTIVE_LOSSES: ViolationType.CONSECUTIVE_LOSS,
        AutoDisableTriggerType.DAILY_LOSS: ViolationType.DAILY_LOSS,
        AutoDisableTriggerType.WEEKLY_LOSS: ViolationType.DAILY_LOSS,
        AutoDisableTriggerType.MONTHLY_LOSS: ViolationType.DAILY_LOSS,
        AutoDisableTriggerType.WIN_RATE_DROP: ViolationType.DAILY_LOSS,
        AutoDisableTriggerType.DRAWDOWN: ViolationType.DRAWDOWN,
    }

    @classmethod
    def evaluate(cls, session, stats, capital):
        rules = session.strategy.auto_disable_rules.filter(is_active=True)
        if not rules.exists():
            return None

        evaluation = RiskEvaluator(capital).evaluate_auto_disable_rules(rules, stats)
        if not evaluation.get("should_disable"):
            return None

        match = (evaluation.get("matches") or [{}])[0]
        message = match.get("message", "Strategy auto-disable triggered")
        session.status = "PAUSED"
        session.error_message = message
        session.save(update_fields=["status", "error_message", "updated_at"])

        violation_type = cls.VIOLATION_TYPES.get(
            match.get("trigger_type"),
            ViolationType.CONSECUTIVE_LOSS,
        )
        RiskViolation.objects.create(
            user=session.user,
            strategy=session.strategy,
            violation_type=violation_type,
            severity=Severity.CRITICAL,
            message=f"Strategy auto-disable triggered: {message}",
            threshold_value=match.get("threshold"),
            actual_value=match.get("actual_value"),
            action_taken=ViolationAction.DISABLED,
        )
        try:
            NotificationService.notify(
                user=session.user,
                title="Strategy Auto-Paused",
                message=f"Session for '{session.strategy.name}' was paused: {message}",
                notification_type=NotificationType.STRATEGY_PAUSED,
                severity=Severity.CRITICAL,
                strategy=session.strategy,
                data={"session_id": str(session.id), "module": session._meta.app_label},
            )
        except Exception:
            logger.exception("Failed dispatching auto-disable notification for session %s", session.id)
        return match
