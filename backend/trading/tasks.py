import logging
from celery import shared_task
from .services import TradingOrderService

logger = logging.getLogger(__name__)

@shared_task(name="trading.process_terminal_tick", queue="tick")
def process_terminal_tick(symbol, quote):
    """
    Asynchronous task to process the manual trading matching engine for a given tick.
    """
    try:
        TradingOrderService.process_matching_engine(symbol, quote)
    except Exception as exc:
        logger.exception("Error in process_terminal_tick for %s: %s", symbol, exc)
        return {"status": "error", "error": str(exc)}
    return {"status": "processed", "symbol": symbol}
