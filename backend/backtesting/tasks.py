import logging
from celery import shared_task
from django.utils import timezone
from .models import BacktestRun, MonteCarloRun
from .engine import BacktestEngine
from common.enums import BacktestStatus

logger = logging.getLogger(__name__)

@shared_task(bind=True, name='backtesting.run_backtest')
def run_backtest_task(self, run_id):
    """
    Celery task to run a single backtest.
    """
    try:
        run = BacktestRun.objects.get(id=run_id)
        engine = BacktestEngine(run_id)
        engine.run_simulation()
        run.refresh_from_db(fields=["status", "error_message"])
        if run.status == BacktestStatus.FAILED:
            return f"Backtest {run_id} failed: {run.error_message}"
        if run.status == BacktestStatus.CANCELLED:
            return f"Backtest {run_id} cancelled"
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
