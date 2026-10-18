from django.db import transaction
from django.utils import timezone
from common.enums import NotificationType
from core.lifecycle import publish_session_event
from core.shared_state_store import shared_state_store
from notifications.services import NotificationService
from .policy import evaluate_configuration, pause_state, release_state


class AutoDisableGate:
    """Persist risk pauses using the session's pinned strategy configuration."""

    @staticmethod
    def configuration(session):
        allocation = session.allocation
        if not allocation or not allocation.deployed_version:
            raise ValueError("A deployed strategy snapshot is required for execution.")
        return allocation.deployed_version.config_snapshot

    @classmethod
    def release(cls, session):
        from strategy_engine.runtime import StrategyRuntimeState
        scope = "live" if session._meta.app_label == "live_trading" else "paper"
        StrategyRuntimeState.ensure_risk_metrics(scope, session.pk)
        stats = shared_state_store.get_risk_metrics(scope, session.pk)
        state = session.auto_disable_state
        if state.get("version_id") != session.allocation.deployed_version_id:
            state = {}
        session.auto_disable_state = release_state(state, stats)
        session.auto_disable_state["version_id"] = session.allocation.deployed_version_id
        release = session.auto_disable_state["release"]
        transaction.on_commit(lambda: shared_state_store.update_risk_metrics(scope, session.pk, {
            "auto_disable_release": release}), robust=True)

    @staticmethod
    def version_changed(session):
        """A resume acknowledgement applies only to the version that was paused."""
        session.auto_disable_state = {}
        session.save(update_fields=["auto_disable_state", "updated_at"])
        scope = "live" if session._meta.app_label == "live_trading" else "paper"
        transaction.on_commit(lambda: shared_state_store.update_risk_metrics(scope, session.pk, {
            "auto_disable_release": {}, "risk_metrics_version": None}), robust=True)

    @classmethod
    def record_close(cls, session, trade_id, pnl, timestamp, capital, config=None):
        """Called after commit; publish fresh counters before checking restrictions."""
        from strategy_engine.runtime import StrategyRuntimeState
        scope = "live" if session._meta.app_label == "live_trading" else "paper"
        config = config if config is not None else cls.configuration(session)
        stats = StrategyRuntimeState.record_risk_close(scope, session.pk, trade_id, pnl, timestamp, capital, config)
        cls.after_close(session, stats, capital, config)

    @classmethod
    def after_close(cls, session, stats, capital, config):
        match = cls.evaluate(session, stats, capital, config=config)
        if match and match["paused_now"]:
            scope = "live" if session._meta.app_label == "live_trading" else "paper"
            publish_session_event(scope, session, "SESSION_PAUSE")

    @classmethod
    def evaluate(cls, session, stats, capital, config=None):
        config = config if config is not None else cls.configuration(session)
        evaluation = evaluate_configuration(config, stats, capital, timezone.now(),
                                             session.auto_disable_state.get("release"))
        if not evaluation["should_disable"]:
            return None
        match = dict(evaluation["matches"][0])
        message = match["message"]
        with transaction.atomic():
            locked = session.__class__.objects.select_for_update(of=("self",)).select_related("strategy", "user", "allocation").get(pk=session.pk)
            if not locked.allocation or locked.allocation.deployed_version_id != session.allocation.deployed_version_id:
                match["paused_now"] = False
                match["message"] = "The deployed strategy version changed. Retry with the current configuration."
                return match
            paused_now = locked.status == "RUNNING"
            if paused_now:
                locked._audit_actor = "System"
                locked._audit_reason = message
                locked.status = "PAUSED"
                locked.error_message = message
                locked.auto_disable_state = pause_state(evaluation, timezone.now())
                locked.auto_disable_state["version_id"] = session.allocation.deployed_version_id
                locked.save(update_fields=["status", "error_message", "auto_disable_state", "updated_at"])
                scope = "live" if locked._meta.app_label == "live_trading" else "paper"
                NotificationService.notify(
                    user=locked.user, type=NotificationType.WARNING,
                    title=f"{scope.title()} strategy auto-paused: {locked.strategy.name}",
                    message=message,
                    data={"module": scope, "session_id": str(locked.pk), "strategy_id": str(locked.strategy_id),
                          "strategy_name": locked.strategy.name, "matched_rules": evaluation["matches"],
                          "resume_at": locked.auto_disable_state["resume_at"]},
                    dedupe_key=f"auto-disable:{scope}:{locked.pk}:{locked.updated_at.isoformat()}",
                )
            session.status = locked.status
            session.error_message = locked.error_message
            session.auto_disable_state = locked.auto_disable_state
        match["paused_now"] = paused_now
        return match
