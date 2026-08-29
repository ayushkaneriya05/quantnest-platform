"""
EventCalendarService — Market event calendar for special event filtering.

Used by both BacktestEngine and PaperExecutionService to avoid trading on
earnings days, RBI policy dates, major news events, and other configurable dates.
"""
import logging
from datetime import date
from functools import lru_cache

from .models import MarketEvent

logger = logging.getLogger(__name__)


@lru_cache(maxsize=50000)
def _cached_is_event_day(target_date_str, event_type, instrument_id):
    qs = MarketEvent.objects.filter(event_date=target_date_str, event_type=event_type)
    if instrument_id is not None:
        from django.db.models import Q
        qs = qs.filter(Q(instrument_id=instrument_id) | Q(instrument__isnull=True))
    else:
        qs = qs.filter(instrument__isnull=True)
    return qs.exists()


class EventCalendarService:
    """
    Service for checking and managing market event calendar data.
    Supports earnings, RBI policy, news, and custom event types.
    """

    @staticmethod
    def is_event_day(target_date, event_type, instrument=None):
        """
        Check whether *target_date* is marked with an event of *event_type*.

        For instrument-specific events (EARNINGS, NEWS) the function checks
        both instrument-specific records **and** market-wide records (instrument=NULL).
        For market-wide events (RBI_POLICY, BUDGET, etc.) only NULL-instrument
        records are checked.
        """
        if isinstance(target_date, str):
            try:
                target_date_str = target_date
            except (ValueError, TypeError):
                return False
        else:
            target_date_str = target_date.isoformat()

        instrument_id = getattr(instrument, "id", instrument) if instrument else None
        return _cached_is_event_day(target_date_str, event_type, instrument_id)

    @staticmethod
    def get_events(date_from, date_to, event_types=None):
        """
        Retrieve all market events within a date range, optionally filtered by type.
        """
        qs = MarketEvent.objects.filter(event_date__gte=date_from, event_date__lte=date_to)
        if event_types:
            qs = qs.filter(event_type__in=event_types)
        return qs.select_related("instrument")
