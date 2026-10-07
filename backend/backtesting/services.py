"""Shared backtest creation and dispatch, including approved research snapshots."""
import logging
from copy import deepcopy
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.enums import BacktestStatus
from strategies.services import StrategySnapshotService
from .models import BacktestRun

logger = logging.getLogger(__name__)


def backtest_configuration(run):
    """The same effective snapshot for execution, research and approved reruns."""
    snapshot = run.strategy_version.config_snapshot if run.strategy_version_id else run.config_snapshot
    config = deepcopy(snapshot or {})
    def merge(base, updates):
        for key, value in (updates or {}).items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merge(base[key], value)
            else:
                base[key] = deepcopy(value)
    merge(config, run.parameters)
    return config


@transaction.atomic
def create_backtest(serializer, user, *, approved_snapshot=None):
    strategy = serializer.validated_data["strategy"]
    if strategy.user_id != user.pk:
        raise ValidationError({"strategy": "Select one of your own strategies."})
    version = None
    if approved_snapshot is None:
        version = StrategySnapshotService.create_snapshot(strategy, user=user,
                    change_notes=f"Auto-snapshot for backtest: {serializer.validated_data.get('name', 'Unnamed')}")
        approved_snapshot = version.config_snapshot
    if not approved_snapshot.get("watchlist_instruments"):
        raise ValidationError({"strategy": "Strategy has no watchlist instruments."})
    if not any(group.get("rule_type") == "ENTRY" and group.get("is_active", True) and
               any(rule.get("is_active", True) for rule in group.get("rules", []))
               for group in approved_snapshot.get("rule_groups", [])):
        raise ValidationError({"strategy": "Strategy needs at least one active entry rule."})
    return serializer.save(user=user, strategy_version=version, config_snapshot=approved_snapshot)


def start_backtest(run, *, on_dispatch=None):
    updated = BacktestRun.objects.filter(pk=run.pk, status=BacktestStatus.PENDING).update(
        status=BacktestStatus.RUNNING, started_at=timezone.now(), error_message="", progress_pct=0,
        progress_message="Starting backtest and loading historical candles...")
    if not updated:
        raise ValidationError("This backtest has already been started.")
    run.refresh_from_db()

    def dispatch():
        from .tasks import run_backtest_task
        error = ""
        try:
            run_backtest_task.delay(run.pk)
        except Exception:
            logger.exception("Could not queue backtest %s", run.pk)
            error = "Backtest queue is unavailable. Start the worker and try again."
            BacktestRun.objects.filter(pk=run.pk, status=BacktestStatus.RUNNING).update(
                status=BacktestStatus.PENDING, started_at=None, error_message=error, progress_message=error)
        if on_dispatch:
            on_dispatch(error)
    transaction.on_commit(dispatch)
    return run
