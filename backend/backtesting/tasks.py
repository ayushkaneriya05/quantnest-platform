import logging
from celery import shared_task
from django.utils import timezone
from .models import BacktestMetrics, BacktestRun, MonteCarloRun
from .engine import BacktestEngine
from common.enums import BacktestStatus, NotificationType
from notifications.services import NotificationService

logger = logging.getLogger(__name__)


def _notify_backtest_result(run):
    status = run.status
    notification_type = {
        BacktestStatus.COMPLETED: NotificationType.INFO,
        BacktestStatus.CANCELLED: NotificationType.INFO,
        BacktestStatus.FAILED: NotificationType.CRITICAL,
    }.get(status)
    if notification_type is None:
        return

    title = {
        BacktestStatus.COMPLETED: f"Backtest completed: {run.name}",
        BacktestStatus.CANCELLED: f"Backtest cancelled: {run.name}",
        BacktestStatus.FAILED: f"Backtest failed: {run.name}",
    }[status]
    if status == BacktestStatus.COMPLETED:
        metrics = BacktestMetrics.objects.filter(run=run).first()
        summary = (
            f"{metrics.total_trades} trades; final capital {metrics.final_capital}."
            if metrics else "Results are ready to review."
        )
        message = f"{run.strategy.name} ({run.start_date} to {run.end_date}) finished. {summary}"
    elif status == BacktestStatus.CANCELLED:
        message = f"{run.strategy.name} ({run.start_date} to {run.end_date}) was cancelled."
    else:
        message = run.error_message or "The backtest stopped because of an unexpected error."
        message = f"{run.strategy.name}: {message[:1200]}"

    NotificationService.notify(
        user=run.user,
        type=notification_type,
        title=title,
        message=message,
        data={"module": "backtest", "backtest_run_id": str(run.pk), "strategy_id": str(run.strategy_id), "strategy_name": run.strategy.name, "status": status},
        dedupe_key=f"backtest:{run.pk}:{status}",
    )

@shared_task(bind=True, name='backtesting.run_backtest')
def run_backtest_task(self, run_id):
    """
    Celery task to run a single backtest.
    """
    try:
        run = BacktestRun.objects.select_related("user", "strategy").get(id=run_id)
        engine = BacktestEngine(run_id)
        engine.run_simulation()
        run.refresh_from_db(fields=["status", "error_message"])
        if run.status == BacktestStatus.FAILED:
            _notify_backtest_result(run)
            return f"Backtest {run_id} failed: {run.error_message}"
        if run.status == BacktestStatus.CANCELLED:
            _notify_backtest_result(run)
            return f"Backtest {run_id} cancelled"
        _notify_backtest_result(run)
        try:
            from gamification.services import GamificationService
            from platform_events.services import ActivityService, DomainEventService

            event = DomainEventService.emit(
                "BACKTEST_FINISHED",
                user=run.user,
                source=run,
                source_app="backtesting",
                payload={"strategy": run.strategy_id, "status": run.status},
            )
            ActivityService.create(
                run.user,
                "STRATEGY_DEPLOYED",
                f"Backtest completed: {run.name}",
                target=run,
                domain_event=event,
                strategy=run.strategy,
                visibility="PRIVATE",
                metadata={"source": "backtest"},
            )
            GamificationService.grant_xp(run.user, "BACKTEST_FINISHED", 25, source=run)
        except Exception:
            pass
        return f"Backtest {run_id} completed successfully"
    except Exception as e:
        logger.exception(f"Error in backtest task {run_id}: {str(e)}")
        # Update run status if not already handled by engine
        BacktestRun.objects.filter(id=run_id).update(
            status=BacktestStatus.FAILED,
            error_message=str(e),
            completed_at=timezone.now()
        )
        failed_run = BacktestRun.objects.select_related("user", "strategy").filter(id=run_id).first()
        if failed_run:
            _notify_backtest_result(failed_run)
        return f"Backtest {run_id} failed: {str(e)}"



@shared_task(bind=True, name='backtesting.run_monte_carlo')
def run_monte_carlo_task(self, mc_id):
    """
    Celery task to run Monte Carlo simulations.
    """
    from .monte_carlo import MonteCarloSimulator
    try:
        simulator = MonteCarloSimulator(mc_id)
        simulator.run_simulation()
        return f"Monte Carlo {mc_id} completed successfully"
    except Exception as e:
        logger.exception(f"Error in monte carlo task {mc_id}: {str(e)}")
        MonteCarloRun.objects.filter(id=mc_id).update(
            status=BacktestStatus.FAILED,
            completed_at=timezone.now()
        )
        return f"Monte Carlo {mc_id} failed: {str(e)}"
