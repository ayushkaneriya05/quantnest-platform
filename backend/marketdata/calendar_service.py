"""
EventCalendarService — Market event calendar for special event filtering.

Used by both BacktestEngine and PaperStrategyEngine to avoid trading on
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

    # ── Predefined RBI MPC Policy announcement dates ──
    RBI_POLICY_DATES = {
        2024: ["2024-02-08", "2024-04-05", "2024-06-07", "2024-08-08", "2024-10-09", "2024-12-06"],
        2025: ["2025-02-07", "2025-04-09", "2025-06-06", "2025-08-08", "2025-10-01", "2025-12-05"],
        2026: ["2026-02-06", "2026-04-09", "2026-06-05", "2026-08-07", "2026-10-09", "2026-12-04"],
    }

    # ─── Core Queries ────────────────────────────────────────────

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

    @staticmethod
    def get_events_for_instrument(instrument, date_from, date_to, event_types=None):
        """
        Retrieve events relevant to a specific instrument, including market-wide events.
        """
        from django.db.models import Q

        instrument_id = getattr(instrument, "id", instrument)
        qs = MarketEvent.objects.filter(
            event_date__gte=date_from,
            event_date__lte=date_to,
        ).filter(Q(instrument_id=instrument_id) | Q(instrument__isnull=True))

        if event_types:
            qs = qs.filter(event_type__in=event_types)
        return qs.select_related("instrument")

    # ─── Seeding Methods ─────────────────────────────────────────

    @classmethod
    def seed_rbi_policy_dates(cls, *years):
        """
        Seed known RBI MPC policy dates from the hardcoded calendar.
        """
        created = 0
        for year in years:
            for raw_date in cls.RBI_POLICY_DATES.get(int(year), []):
                _, was_created = MarketEvent.objects.get_or_create(
                    event_type="RBI_POLICY",
                    event_date=date.fromisoformat(raw_date),
                    instrument=None,
                    defaults={
                        "title": f"RBI MPC Policy Decision {raw_date}",
                        "description": "Scheduled RBI Monetary Policy Committee announcement.",
                        "impact": "WARNING",
                        "source": "Manual seed",
                    },
                )
                if was_created:
                    created += 1
        return created

    @staticmethod
    def seed_earnings_event(instrument, event_date, title=None, source="Manual"):
        """
        Create an EARNINGS event for a specific instrument on a given date.
        """
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        instrument_name = getattr(instrument, "symbol", str(instrument))
        _, was_created = MarketEvent.objects.get_or_create(
            event_type="EARNINGS",
            event_date=event_date,
            instrument=instrument,
            defaults={
                "title": title or f"Earnings Announcement - {instrument_name}",
                "description": f"Quarterly earnings announcement for {instrument_name}.",
                "impact": "WARNING",
                "source": source,
            },
        )
        return was_created

    @staticmethod
    def seed_news_event(event_date, title, description="", instrument=None, source="Manual"):
        """
        Create a NEWS event, optionally tied to a specific instrument.
        """
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        _, was_created = MarketEvent.objects.get_or_create(
            event_type="NEWS",
            event_date=event_date,
            instrument=instrument,
            defaults={
                "title": title,
                "description": description,
                "impact": "CRITICAL",
                "source": source,
            },
        )
        return was_created

    @staticmethod
    def bulk_seed_events(events):
        """
        Bulk-seed multiple events.

        Each item in *events* should be a dict with keys:
            event_type, event_date, title,
            description (optional), impact (optional),
            instrument (optional), source (optional)
        """
        created = 0
        for event_data in events:
            event_date = event_data.get("event_date")
            if isinstance(event_date, str):
                event_date = date.fromisoformat(event_date)

            _, was_created = MarketEvent.objects.get_or_create(
                event_type=event_data["event_type"],
                event_date=event_date,
                instrument=event_data.get("instrument"),
                defaults={
                    "title": event_data.get("title", "Market Event"),
                    "description": event_data.get("description", ""),
                    "impact": event_data.get("impact", "WARNING"),
                    "source": event_data.get("source", "Bulk seed"),
                },
            )
            if was_created:
                created += 1
        return created
