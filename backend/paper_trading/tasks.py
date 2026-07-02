import logging
from celery import shared_task
from .services import PaperStrategyEngine, PortfolioService
from .models import Portfolio

logger = logging.getLogger(__name__)

@shared_task(name="paper_trading.process_paper_tick", queue="tick")
def process_paper_tick(symbol, quote=None, quote_already_cached=False):
    """
    Asynchronous task to process paper trading strategies for a given symbol tick.
    """
    try:
        PaperStrategyEngine.execute_live_tick(
            symbol,
            quote=quote,
            quote_already_cached=quote_already_cached,
        )
    except Exception as exc:
        logger.exception("Error in process_paper_tick for %s: %s", symbol, exc)
        return {"status": "error", "error": str(exc)}
    return {"status": "processed", "symbol": symbol}


@shared_task(name="paper_trading.daily_performance_snapshot")
def daily_performance_snapshot():
    created = 0
    for portfolio in Portfolio.objects.filter(is_active=True):
        PortfolioService.take_daily_snapshot(portfolio)
        created += 1
    return {"snapshots": created}


@shared_task(name="paper_trading.exposure_snapshot")
def exposure_snapshot():
    created = 0
    for portfolio in Portfolio.objects.filter(is_active=True):
        PortfolioService.take_exposure_snapshot(portfolio)
        created += 1
    return {"snapshots": created}


@shared_task(name="paper_trading.rebalance_all_portfolios")
def rebalance_all_portfolios():
    """Nightly task to rebalance percentage-based allocations."""
    rebalanced = 0
    for portfolio in Portfolio.objects.filter(is_active=True):
        rebalanced += PortfolioService.rebalance_allocations(portfolio) or 0
    return {"allocations_rebalanced": rebalanced}
