import logging
from celery import shared_task
from django.utils import timezone
from .models import BacktestRun, MonteCarloRun
from .engine import BacktestEngine
from .services import notify_backtest_result, publish_backtest_update
from common.enums import BacktestStatus

logger = logging.getLogger(__name__)


@shared_task(name='backtesting.run_backtest')
def run_backtest_task(run_id):
    """
    Celery task to run a single backtest.
    """
    # The job owns its execution state; redelivery cannot start it twice.
    if not BacktestRun.objects.filter(pk=run_id, status=BacktestStatus.QUEUED).update(status=BacktestStatus.RUNNING, started_at=timezone.now()):
        return
    try:
        run = BacktestRun.objects.select_related("user", "strategy").get(id=run_id)
        engine = BacktestEngine(run_instance=run)
        engine.run_simulation()
        run.refresh_from_db(fields=["status", "error_message"])
        notify_backtest_result(run)
        if run.status == BacktestStatus.FAILED:
            return f"Backtest {run_id} failed: {run.error_message}"
        if run.status == BacktestStatus.CANCELLED:
            return f"Backtest {run_id} cancelled"
        return f"Backtest {run_id} completed successfully"
    except Exception as e:
        logger.exception(f"Error in backtest task {run_id}: {str(e)}")
        # Update run status if not already handled by engine
        BacktestRun.objects.filter(id=run_id).exclude(status__in=[BacktestStatus.COMPLETED, BacktestStatus.CANCELLED]).update(
            status=BacktestStatus.FAILED,
            error_message=str(e),
            progress_message=f"Backtest failed: {e}"[:255],
            completed_at=timezone.now()
        )
        failed_run = BacktestRun.objects.select_related("user", "strategy").filter(id=run_id).first()
        if failed_run:
            publish_backtest_update(failed_run)
            notify_backtest_result(failed_run)
        return f"Backtest {run_id} failed: {str(e)}"



@shared_task(name='backtesting.run_monte_carlo')
def run_monte_carlo_task(mc_id):
    """
    Celery task to run Monte Carlo simulations.
    """
    from .monte_carlo import MonteCarloSimulator
    if not MonteCarloRun.objects.filter(pk=mc_id, status=BacktestStatus.QUEUED).update(status=BacktestStatus.RUNNING):
        return
    try:
        simulator = MonteCarloSimulator(mc_id)
        simulator.run_simulation()
        simulator.run.refresh_from_db(fields=["status", "error_message"])
        if simulator.run.status == BacktestStatus.FAILED:
            return f"Monte Carlo {mc_id} failed: {simulator.run.error_message}"
        return f"Monte Carlo {mc_id} completed successfully"
    except Exception as e:
        logger.exception(f"Error in monte carlo task {mc_id}: {str(e)}")
        MonteCarloRun.objects.filter(id=mc_id).update(
            status=BacktestStatus.FAILED,
            error_message=str(e),
            completed_at=timezone.now()
        )
        return f"Monte Carlo {mc_id} failed: {str(e)}"
