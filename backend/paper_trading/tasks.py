import logging
from celery import shared_task
from .services import PortfolioService
from .models import Portfolio

logger = logging.getLogger(__name__)


@shared_task(name="paper_trading.daily_performance_snapshot")
def daily_performance_snapshot():
    created = 0
    for portfolio in Portfolio.objects.filter(is_active=True):
        PortfolioService.take_daily_snapshot(portfolio)
        created += 1
    return {"snapshots": created}


@shared_task(name="paper_trading.rebalance_all_portfolios")
def rebalance_all_portfolios():
    """Nightly task to rebalance percentage-based allocations."""
    rebalanced = 0
    for portfolio in Portfolio.objects.filter(is_active=True):
        rebalanced += PortfolioService.rebalance_allocations(portfolio) or 0
    return {"allocations_rebalanced": rebalanced}
