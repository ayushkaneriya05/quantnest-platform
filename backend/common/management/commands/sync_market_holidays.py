"""
management/commands/sync_market_holidays.py

Populates MarketHoliday for every active ExchangeConfig row.
"""
import datetime as dt
import logging
import time

import requests
from django.core.management.base import BaseCommand

from common.models import ExchangeConfig, MarketHoliday

logger = logging.getLogger(__name__)

try:
    import pandas_market_calendars as mcal
except ImportError:
    mcal = None

NSE_API_SEGMENT_FOR_EXCHANGE = {
    "NSE": "CM",
    "BSE": "CM",   # BSE mirrors NSE's equity (CM) segment
}

PMC_FALLBACK_CALENDAR_FOR_EXCHANGE = {
    "NSE": "NSE",
    "BSE": "BSE"
}

NSE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class Command(BaseCommand):
    help = "Sync MarketHoliday rows from pandas_market_calendars (NSE/BSE/NFO/BFO) and NSE's live API (MCX/CDS)."

    def add_arguments(self, parser):
        today = dt.date.today()
        parser.add_argument("--start-year", type=int, default=today.year - 1)
        parser.add_argument("--end-year", type=int, default=today.year + 2)

    def handle(self, *args, **options):
        start_year, end_year = options["start_year"], options["end_year"]
        configs = {c.exchange: c for c in ExchangeConfig.objects.filter(is_active=True)}

        if not configs:
            self.stderr.write(self.style.ERROR(
                "No active ExchangeConfig rows found. Create these first (via admin/fixture) - this command only fills in holidays "
                "for exchanges you've already configured."
            ))
            return

        totals = {"added": 0, "updated": 0, "unchanged": 0, "skipped_exchanges": [], "fallback_used": []}

        for exchange_code, nse_segment in NSE_API_SEGMENT_FOR_EXCHANGE.items():
            config = configs.get(exchange_code)
            if config is None:
                continue  # not configured on this platform, skip quietly

            try:
                self._sync_from_nse_api(config, nse_segment, totals)
                continue
            except Exception as exc:
                logger.warning("NSE live API sync failed for %s: %s", exchange_code, exc)

            # Fell through: live API failed. Try the fallback if one exists.
            pmc_name = PMC_FALLBACK_CALENDAR_FOR_EXCHANGE.get(exchange_code)
            if pmc_name is None or mcal is None:
                totals["skipped_exchanges"].append(exchange_code)
                continue

            try:
                self._sync_from_pandas_market_calendars(config, pmc_name, start_year, end_year, totals)
                totals["fallback_used"].append(exchange_code)
            except Exception:
                logger.exception("pandas_market_calendars fallback also failed for %s", exchange_code)
                totals["skipped_exchanges"].append(exchange_code)

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {totals['added']} added, {totals['updated']} updated, "
            f"{totals['unchanged']} unchanged. "
            f"Fallback used for: {totals['fallback_used'] or 'none'}. "
            f"Skipped entirely: {totals['skipped_exchanges'] or 'none'}"
        ))

    # -------------------------------------------------------------------
    def _upsert(self, config, holiday_date, description, totals, is_partial=False, partial_close=None):
        obj, created = MarketHoliday.objects.update_or_create(
            exchange=config,
            date=holiday_date,
            defaults={
                "description": description,
                "is_partial": is_partial,
                "partial_close": partial_close,
            },
        )
        if created:
            totals["added"] += 1
        elif obj.description != description:
            totals["updated"] += 1
        else:
            totals["unchanged"] += 1

    def _sync_from_pandas_market_calendars(self, config, pmc_name, start_year, end_year, totals):
        """Fallback path: dates only, no holiday names available from this
        library, so we store a generic description rather than inventing one."""
        calendar = mcal.get_calendar(pmc_name)
        start = dt.date(start_year, 1, 1)
        end = dt.date(end_year, 12, 31)

        schedule = calendar.schedule(start_date=start, end_date=end)
        trading_days = set(schedule.index.date)

        all_days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
        weekday_holidays = [d for d in all_days if d.weekday() < 5 and d not in trading_days]

        for holiday_date in weekday_holidays:
            self._upsert(config, holiday_date, "Market holiday", totals)

    def _sync_from_nse_api(self, config, nse_segment, totals):
        session = requests.Session()
        session.headers.update({
            "User-Agent": NSE_USER_AGENT, "Accept": "application/json, text/plain, */*",
        })
        session.get("https://www.nseindia.com", timeout=15)
        resp = None
        for attempt in range(3):
            resp = session.get(
                "https://www.nseindia.com/api/holiday-master", params={"type": "trading"}, timeout=15,
            )
            if resp.status_code == 200:
                break
            time.sleep(3 * (attempt + 1))
        if resp is None or resp.status_code != 200:
            raise RuntimeError(f"NSE API returned {resp.status_code if resp else 'no response'}")

        data = resp.json().get(nse_segment, [])
        for entry in data:
            raw_date = entry.get("tradingDate") or entry.get("date")
            if not raw_date:
                continue
            holiday_date = None
            for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
                try:
                    holiday_date = dt.datetime.strptime(raw_date.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            if holiday_date is None:
                continue
            description = (entry.get("description") or "Market holiday").strip()
            self._upsert(config, holiday_date, description, totals)
