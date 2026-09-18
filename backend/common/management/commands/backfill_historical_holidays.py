"""
management/commands/backfill_historical_holidays.py

Usage:
    python manage.py backfill_historical_holidays --start-year 1997
    python manage.py backfill_historical_holidays --start-year 2015 --end-year 2023
"""
import datetime as dt

from django.core.management.base import BaseCommand

from common.models import ExchangeConfig, MarketHoliday

try:
    import pandas_market_calendars as mcal
except ImportError:
    mcal = None

PMC_CALENDAR_FOR_EXCHANGE = {
    "NSE": "NSE",
    "BSE": "BSE"
}


class Command(BaseCommand):
    help = "One-time deep historical backfill of NSE/BSE/NFO/BFO holidays via pandas_market_calendars."

    def add_arguments(self, parser):
        parser.add_argument("--start-year", type=int, default=1997)
        parser.add_argument("--end-year", type=int, default=dt.date.today().year)

    def handle(self, *args, **options):
        if mcal is None:
            self.stderr.write(self.style.ERROR("pandas_market_calendars is not installed."))
            return

        start_year, end_year = options["start_year"], options["end_year"]
        configs = {c.exchange: c for c in ExchangeConfig.objects.filter(is_active=True)}

        totals = {"added": 0, "updated": 0, "unchanged": 0}
        for exchange_code, pmc_name in PMC_CALENDAR_FOR_EXCHANGE.items():
            config = configs.get(exchange_code)
            if config is None:
                continue

            calendar = mcal.get_calendar(pmc_name)
            start = dt.date(start_year, 1, 1)
            end = dt.date(end_year, 12, 31)
            schedule = calendar.schedule(start_date=start, end_date=end)
            trading_days = set(schedule.index.date)

            all_days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
            weekday_holidays = [d for d in all_days if d.weekday() < 5 and d not in trading_days]

            for holiday_date in weekday_holidays:
                obj, created = MarketHoliday.objects.update_or_create(
                    exchange=config,
                    date=holiday_date,
                    defaults={"description": "Market holiday"},
                )
                totals["added" if created else "unchanged"] += 1

            self.stdout.write(f"{exchange_code}: {len(weekday_holidays)} holiday dates from {start_year}-{end_year}")

        self.stdout.write(self.style.SUCCESS(f"Backfill complete: {totals}"))
