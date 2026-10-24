"""Sync NSE segment holidays, mirrored to BSE and MCX calendars."""
from datetime import date, datetime, time

import pandas as pd
import pandas_market_calendars as mcal
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from common.enums import Exchange, FyersSegment
from common.models import ExchangeConfig, MarketHoliday


NSE_SEGMENTS = {
    FyersSegment.CAPITAL_MARKET: "CM",
    FyersSegment.EQUITY_DERIVATIVES: "FO",
    FyersSegment.CURRENCY_DERIVATIVES: "CD",
    FyersSegment.COMMODITY_DERIVATIVES: "COM",
}
# NSE commodity holiday circular: morning ends and evening begins at 17:00 IST.
COMMODITY_SESSION_SPLIT = time(17)
HOLIDAY_FIELDS = ("description", "is_partial", "partial_open", "partial_close")


class Command(BaseCommand):
    help = "Sync current-year NSE API holidays and historical NSE library dates for all active segments."

    def add_arguments(self, parser):
        parser.add_argument("--start-year", type=int, help="First year to sync (default: current year).")
        parser.add_argument("--end-year", type=int, help="Last year to sync (default: current year).")

    def handle(self, *args, **options):
        current_year = timezone.localdate().year
        start = options["start_year"] if options["start_year"] is not None else current_year
        end = options["end_year"] if options["end_year"] is not None else current_year
        if not 1 <= start <= end <= current_year:
            raise CommandError(f"Use 1 <= start-year <= end-year <= {current_year}; future calendars are not imported.")
        configs = list(ExchangeConfig.objects.filter(is_active=True, exchange__in=Exchange.values))
        if not configs:
            raise CommandError("No active segment calendars. Run migrations first.")
        segments = {config.segment for config in configs}
        if segments - NSE_SEGMENTS.keys():
            raise CommandError("An active calendar has an unsupported segment. Review Exchange configurations in Admin.")
        holidays = {segment: {} for segment in segments}

        if start < current_year:
            dates = pd.DatetimeIndex(mcal.get_calendar("NSE").holidays().holidays).date
            historical_end = min(end, current_year - 1)
            if not len(dates) or start < min(dates).year or historical_end > max(dates).year:
                raise CommandError("Requested historical years are outside the installed NSE library's coverage.")
            history = {
                day: {"description": "NSE library holiday", "is_partial": False,
                      "partial_open": None, "partial_close": None}
                for day in dates if start <= day.year <= historical_end
            }
            for segment in segments:
                holidays[segment].update(history)
            self.stdout.write(f"History {start}-{historical_end}: {len(history)} shared NSE library dates per segment.")

        if end == current_year:
            try:
                current = self.fetch_current_holidays(current_year, segments)
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                raise CommandError(f"NSE holiday sync failed; existing dates were retained: {exc}") from exc
            for segment in segments:
                holidays[segment].update(current[segment])

        changed = removed = preserved = 0
        with transaction.atomic():
            for config in configs:
                expected = holidays[config.segment]
                existing = {
                    row.date: row for row in MarketHoliday.objects.select_for_update().filter(
                        exchange=config, date__range=(date(start, 1, 1), date(end, 12, 31)))
                }
                preserved += sum(row.is_partial for row in existing.values())
                obsolete = [row.pk for day, row in existing.items() if not row.is_partial and day not in expected]
                removed += MarketHoliday.objects.filter(pk__in=obsolete).delete()[0]
                updates = []
                for day, values in expected.items():
                    row = existing.get(day)
                    # Keep dated special-session overrides, including weekend openings.
                    if row and row.is_partial:
                        continue
                    if row is None or any(getattr(row, key) != value for key, value in values.items()):
                        updates.append(MarketHoliday(exchange=config, date=day, **values))
                MarketHoliday.objects.bulk_create(
                    updates, update_conflicts=True, unique_fields=["exchange", "date"],
                    update_fields=[*HOLIDAY_FIELDS, "updated_at"], batch_size=1000,
                )
                changed += len(updates)
                self.stdout.write(f"{config.exchange}:{config.get_segment_display()}: {len(expected)} NSE source dates.")
        self.stdout.write(self.style.SUCCESS(
            f"{changed} holiday records added or updated; {removed} obsolete full closures removed; "
            f"{preserved} existing special sessions preserved."
        ))

    @staticmethod
    def fetch_current_holidays(year, segments):
        with requests.Session() as client:
            client.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            client.get("https://www.nseindia.com", timeout=15)
            response = client.get(
                "https://www.nseindia.com/api/holiday-master", params={"type": "trading"}, timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        holidays = {}
        for segment in segments:
            key = NSE_SEGMENTS[segment]
            entries = payload[key]
            if not isinstance(entries, list) or not entries:
                raise ValueError(f"NSE returned an empty or invalid holiday list for {key}.")
            holidays[segment] = {}
            for entry in entries:
                day = datetime.strptime(entry["tradingDate"], "%d-%b-%Y").date()
                if day.year != year:
                    raise ValueError(f"NSE {key} returned {day.year} dates; expected {year}.")
                opening = closing = None
                if segment == FyersSegment.COMMODITY_DERIVATIVES:
                    morning, evening = entry["morning_session"], entry["evening_session"]
                    if morning == "Closed" and evening == "Open":
                        opening = COMMODITY_SESSION_SPLIT
                    elif morning == "Open" and evening == "Closed":
                        closing = COMMODITY_SESSION_SPLIT
                    elif morning != "Closed" or evening != "Closed":
                        raise ValueError("Unrecognised NSE commodity holiday session status.")
                holidays[segment][day] = {
                    "description": entry["description"], "is_partial": opening is not None or closing is not None,
                    "partial_open": opening, "partial_close": closing,
                }
        return holidays
