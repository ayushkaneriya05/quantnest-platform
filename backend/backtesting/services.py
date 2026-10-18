"""Backtest creation, queue submission and user updates."""
from copy import deepcopy
from datetime import datetime, time, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.enums import BacktestStatus
from strategies.services import StrategySnapshotService
from .models import BacktestRun


def publish_backtest_update(run, **details):
    """Publish the same progress payload after committed API or worker changes."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    event_type = {BacktestStatus.COMPLETED: "backtest.completed", BacktestStatus.FAILED: "backtest.error"}.get(run.status, "backtest.progress")
    message = {"run_id": run.pk, "status": run.status, "progress_pct": run.progress_pct,
               "message": run.progress_message, "timestamp": timezone.now().isoformat(), **details}
    if run.status == BacktestStatus.FAILED:
        message["error"] = run.error_message

    def send():
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(f"user_{run.user_id}_backtest", {
                "type": event_type, "message": message})

    transaction.on_commit(send, robust=True)


def notify_backtest_result(run):
    """A notification failure must not change a completed simulation's outcome."""
    from common.enums import NotificationType
    from notifications.services import NotificationService
    from .models import BacktestMetrics
    status = run.status
    if status not in {BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED}:
        return

    def send():
        if status == BacktestStatus.COMPLETED:
            metrics = BacktestMetrics.objects.filter(run=run).first()
            summary = f"{metrics.total_trades} trades; final capital {metrics.final_capital}." if metrics else "Results are ready to review."
            message = f"{run.strategy.name} ({run.start_date} to {run.end_date}) finished. {summary}"
        elif status == BacktestStatus.CANCELLED:
            message = f"{run.strategy.name} ({run.start_date} to {run.end_date}) was cancelled."
        else:
            message = f"{run.strategy.name}: {(run.error_message or 'The backtest stopped because of an unexpected error.')[:1200]}"
        result = {BacktestStatus.COMPLETED: "completed", BacktestStatus.CANCELLED: "cancelled", BacktestStatus.FAILED: "failed"}[status]
        NotificationService.notify(
            user=run.user, type=NotificationType.CRITICAL if status == BacktestStatus.FAILED else NotificationType.INFO,
            title=f"Backtest {result}: {run.name}", message=message,
            data={"module": "backtest", "backtest_run_id": str(run.pk), "strategy_id": str(run.strategy_id),
                  "strategy_name": run.strategy.name, "status": status},
            dedupe_key=f"backtest:{run.pk}:{status}")

    transaction.on_commit(send, robust=True)


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
    from django.contrib.auth import get_user_model
    from strategies.models import Strategy
    get_user_model().objects.select_for_update().get(pk=user.pk)
    strategy = serializer.validated_data["strategy"]
    if strategy.user_id != user.pk:
        raise ValidationError({"strategy": "Select one of your own strategies."})
    strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
    snapshot_current = approved_snapshot is None
    if snapshot_current:
        approved_snapshot = StrategySnapshotService._serialize_strategy(strategy)
    if not approved_snapshot.get("watchlist_instruments"):
        raise ValidationError({"strategy": "Strategy has no watchlist instruments."})
    if not any(group.get("rule_type") == "ENTRY" and group.get("is_active", True) and
               any(rule.get("is_active", True) for rule in group.get("rules", []))
               for group in approved_snapshot.get("rule_groups", [])):
        raise ValidationError({"strategy": "Strategy needs at least one active entry rule."})
    run = serializer.save(user=user, config_snapshot=approved_snapshot)
    if snapshot_current and not run.strategy_version_id:
        version = StrategySnapshotService.create_snapshot(
            strategy, user=user, change_notes=f"Auto-snapshot for backtest: {run.name}",
            config_snapshot=approved_snapshot)
        run.strategy_version = version
        run.save(update_fields=["strategy_version", "updated_at"])
    return run


@transaction.atomic
def start_backtest(run):
    updated = BacktestRun.objects.filter(pk=run.pk, status=BacktestStatus.PENDING).update(
        status=BacktestStatus.QUEUED, error_message="", progress_pct=0,
        progress_message="Queued for historical simulation...")
    if not updated:
        raise ValidationError("This backtest has already been started.")
    run.refresh_from_db()

    from commercial.usage import queue_compute_work
    publish_backtest_update(run)
    queue_compute_work("backtesting.run_backtest", run.pk)
    return run


def estimate_source_workload(config, start_date, end_date):
    """Bound source-candle work using each market's calendar and strategy warmup."""
    from instruments.models import Instrument
    from instruments.services import InstrumentResolver
    from marketdata.calendar import MarketSessionCalendar
    from marketdata.services import MarketDataService
    from marketdata.access import StrategyMarketDataService
    if end_date < start_date or (end_date - start_date).days > 3660:
        raise ValidationError("Choose a valid test range of up to ten years.")
    ids = {int(item["instrument_id"]) for item in config.get("watchlist_instruments", [])}
    instruments = Instrument.objects.in_bulk(ids)
    if not ids or set(instruments) != ids:
        raise ValidationError("All saved instruments must still exist.")
    try:
        InstrumentResolver.validate_execution_snapshot(config)
    except ValueError as exc:
        raise ValidationError(str(exc))
    total, rows = 0, []
    _, timeframes = StrategyMarketDataService.required_timeframes(config)
    families = {"daily" if value in {"1D", "1W"} else "intraday" for value in timeframes}
    for instrument in instruments.values():
        calendar = MarketSessionCalendar.for_instrument(instrument)
        required = MarketDataService.required_1m_candles(config, session_minutes=calendar.session_minutes)
        start = datetime.combine(start_date, time.min, tzinfo=calendar.zone)
        warmup = calendar.warmup_start(start, required, include_weekly="1W" in timeframes)
        calendar.load_holidays(warmup.date(), end_date)
        count, day = 0, warmup.date()
        while day <= end_date:
            if calendar.is_trading_day(day):
                count += 1 if "daily" in families else 0
                if "intraday" in families:
                    count += max(0, int((calendar.session_close(day) - calendar.session_open(day)).total_seconds() // 60))
            day += timedelta(days=1)
        total += count
        rows.append({"instrument_id": instrument.pk, "source_candles": count, "warmup_start": warmup.isoformat()})
    return {"instrument_candles": total, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "rows": rows}
