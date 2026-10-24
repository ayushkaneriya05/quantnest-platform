"""Scheduled maintenance uses the same history ingestion as interactive requests."""
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from instruments.models import Instrument
from .calendar import MarketSessionCalendar
from .contracts import HistoryRequest
from .history import ensure_history
from .live_feed import LiveMarketDataRegistry

logger = logging.getLogger(__name__)


@shared_task(name="marketdata.reconcile_daily_market_data")
def reconcile_daily_market_data():
    now = datetime.now(timezone.utc)
    results = {"changed": 0, "failed": []}
    requirements = LiveMarketDataRegistry.get_state().get("requirements", {})
    symbols = [symbol for symbol, sources in requirements.items() if sources]
    for instrument in Instrument.objects.filter(sym_ticker__in=symbols):
        try:
            calendar = MarketSessionCalendar.for_instrument(instrument)
            day = now.astimezone(calendar.zone).date()
            calendar.load_holidays(day - timedelta(days=14), day + timedelta(days=1))
            closing = datetime.fromtimestamp(calendar.completed_horizon("1D", now), timezone.utc)
            session_day = calendar.session_bounds(closing - timedelta(microseconds=1))[0].date()
            opening = calendar.session_open(session_day)
            for source in requirements[instrument.sym_ticker]:
                result = ensure_history(HistoryRequest(instrument, source, opening, closing, calendar), refresh=True)
                results["changed"] += result.changed
                if result.error:
                    results["failed"].append({"symbol": instrument.sym_ticker, "source": source, "error": result.error})
        except Exception:
            logger.exception("Daily history repair failed symbol=%s", instrument.sym_ticker)
            results["failed"].append({"symbol": instrument.sym_ticker, "error": "History repair failed."})
    return results
