"""Exchange session calendar shared by market-data loading and backtests."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from common.models import ExchangeConfig, MarketHoliday


DEFAULT_EXCHANGE = "NSE"
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_MARKET_OPEN = time(9, 15)
DEFAULT_MARKET_CLOSE = time(15, 30)
INTRADAY_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1H": 60,
    "4H": 240,
}


class MarketSessionCalendar:
    """Market hours, holidays, and candle boundaries for one exchange."""

    def __init__(self, exchange, timezone_name, market_open, market_close):
        self.exchange = exchange
        self.timezone_name = timezone_name or DEFAULT_TIMEZONE
        self.zone = ZoneInfo(self.timezone_name)
        self.market_open = market_open or DEFAULT_MARKET_OPEN
        self.market_close = market_close or DEFAULT_MARKET_CLOSE
        self._holidays = {}
        self._loaded_holiday_ranges = []

    @classmethod
    def for_instrument(cls, instrument):
        return cls.for_exchange(instrument.exchange)

    @classmethod
    def for_exchange(cls, exchange):
        config = ExchangeConfig.objects.filter(exchange=exchange, is_active=True).first()
        return cls(
            exchange=exchange,
            timezone_name=config.timezone if config else DEFAULT_TIMEZONE,
            market_open=config.market_open if config else DEFAULT_MARKET_OPEN,
            market_close=config.market_close if config else DEFAULT_MARKET_CLOSE,
        )

    @classmethod
    def for_symbol(cls, symbol):
        from instruments.models import Instrument

        instrument = Instrument.objects.filter(sym_ticker=str(symbol or "").strip().upper()).only("exchange").first()
        return cls.for_instrument(instrument) if instrument else cls.for_exchange(DEFAULT_EXCHANGE)

    def load_holidays(self, start_date, end_date):
        if any(start <= start_date and end_date <= end for start, end in self._loaded_holiday_ranges):
            return self._holidays
        rows = MarketHoliday.objects.filter(exchange__exchange=self.exchange, date__gte=start_date, date__lte=end_date).only("date", "is_partial", "partial_close")
        self._holidays.update({row.date: row for row in rows})
        self._loaded_holiday_ranges.append((start_date, end_date))
        return self._holidays

    def is_trading_day(self, day, holidays=None):
        holiday = (holidays or self._holidays).get(day)
        return day.weekday() < 5 and (holiday is None or holiday.is_partial)

    def close_time(self, day, holidays=None):
        holiday = (holidays or self._holidays).get(day)
        if holiday and holiday.is_partial and holiday.partial_close:
            return holiday.partial_close
        return self.market_close

    def session_open(self, day):
        return datetime.combine(day, self.market_open, tzinfo=self.zone)

    @property
    def session_minutes(self):
        duration = datetime.combine(date.min, self.market_close) - datetime.combine(date.min, self.market_open)
        return max(int(duration.total_seconds() // 60), 1)

    def warmup_start(self, before, required_minutes, *, include_weekly=False):
        """Find a prior-date boundary containing enough complete source sessions."""
        remaining = max(int(required_minutes or 0), 0)
        before_local = before.astimezone(self.zone)
        if not remaining:
            return before_local

        last_day = before_local.date() - timedelta(days=1)
        calendar_days = max(14, (remaining * 7 // (self.session_minutes * 5)) + 14)
        while True:
            first_day = last_day - timedelta(days=calendar_days)
            holidays = self.load_holidays(first_day, last_day)
            day = last_day
            minutes_remaining = remaining
            oldest_session = None
            while day >= first_day and minutes_remaining > 0:
                if self.is_trading_day(day, holidays):
                    session_minutes = int(
                        (self.session_close(day, holidays) - self.session_open(day)).total_seconds() // 60
                    )
                    if session_minutes > 0:
                        minutes_remaining -= session_minutes
                        oldest_session = day
                day -= timedelta(days=1)
            if minutes_remaining <= 0:
                boundary = oldest_session
                if include_weekly:
                    boundary -= timedelta(days=boundary.weekday())
                return datetime.combine(boundary, time.min, tzinfo=self.zone)
            calendar_days *= 2

    def session_close(self, day, holidays=None):
        return datetime.combine(day, self.close_time(day, holidays), tzinfo=self.zone)

    def expected_1m_timestamps(self, start_dt, end_dt, holidays=None):
        """Expected one-minute candle start times inside a date-time window."""
        start = start_dt.astimezone(self.zone)
        end = end_dt.astimezone(self.zone)
        days = holidays if holidays is not None else self.load_holidays(start.date(), end.date())
        expected = []
        day = start.date()
        while day <= end.date():
            if self.is_trading_day(day, days):
                cursor = max(self.session_open(day), start)
                if cursor.second or cursor.microsecond:
                    cursor = cursor.replace(second=0, microsecond=0) + timedelta(minutes=1)
                session_close = self.session_close(day, days)
                while cursor < session_close and cursor <= end:
                    expected.append(cursor.astimezone(timezone.utc).replace(second=0, microsecond=0))
                    cursor += timedelta(minutes=1)
            day += timedelta(days=1)
        return expected

    @staticmethod
    def _valid_candle(row):
        try:
            open_price = float(row.get("open") or 0)
            high_price = float(row.get("high") or 0)
            low_price = float(row.get("low") or 0)
            close_price = float(row.get("close") or 0)
        except (TypeError, ValueError):
            return False
        return (
            min(open_price, high_price, low_price, close_price) > 0
            and high_price >= low_price
            and low_price <= close_price <= high_price
        )

    def coverage(self, candles, timeframe, start_dt, end_dt):
        """Report missing expected source candles over a requested date range."""
        start = start_dt.astimezone(self.zone)
        end = end_dt.astimezone(self.zone)
        holidays = self.load_holidays(start.date(), end.date())
        if timeframe == "1D":
            expected = {
                day for day in self._date_range(start.date(), end.date())
                if self.is_trading_day(day, holidays)
            }
            actual = {
                datetime.fromtimestamp(row["time"], timezone.utc).astimezone(self.zone).date()
                for row in candles if self._valid_candle(row)
            }
        else:
            expected = set(self.expected_1m_timestamps(start_dt, end_dt, holidays))
            actual = {
                datetime.fromtimestamp(row["time"], timezone.utc).replace(second=0, microsecond=0)
                for row in candles if self._valid_candle(row)
            }
        missing = expected - actual
        missing_dates = sorted({stamp.date() if isinstance(stamp, datetime) else stamp for stamp in missing})
        return {
            "complete": not missing,
            "missing_dates": missing_dates,
            "missing_count": len(missing),
            "available_count": len(actual & expected),
        }

    @staticmethod
    def _date_range(start_date, end_date):
        day = start_date
        while day <= end_date:
            yield day
            day += timedelta(days=1)

    def latest_1m_timestamps(self, count, now=None):
        """Most recent completed market-minute starts, excluding the active minute."""
        count = max(int(count or 0), 0)
        if not count:
            return []
        current = (now or datetime.now(self.zone)).astimezone(self.zone).replace(second=0, microsecond=0)
        latest = current - timedelta(minutes=1)
        earliest = latest.date() - timedelta(days=max(30, count // 150 + 30))
        holidays = self.load_holidays(earliest, latest.date())
        expected = []
        day = latest.date()
        while len(expected) < count:
            if self.is_trading_day(day, holidays):
                cursor = min(self.session_close(day, holidays) - timedelta(minutes=1), latest)
                opening = self.session_open(day)
                while cursor >= opening and len(expected) < count:
                    expected.append(cursor.astimezone(timezone.utc).replace(second=0, microsecond=0))
                    cursor -= timedelta(minutes=1)
            day -= timedelta(days=1)
        return list(reversed(expected))

    def bucket_origin(self, timeframe):
        """Anchor intraday bars at session open and weekly bars at Monday midnight."""
        monday = date(2000, 1, 3)
        bucket_start = datetime.combine(monday, time.min if timeframe == "1W" else self.market_open, tzinfo=self.zone)
        return bucket_start.astimezone(timezone.utc)

    def candle_close(self, timestamp, timeframe, holidays=None):
        """Return the scheduled close instant for a candle bucket."""
        local = timestamp.astimezone(self.zone)
        if timeframe in INTRADAY_MINUTES:
            return min(
                local + timedelta(minutes=INTRADAY_MINUTES[timeframe]),
                self.session_close(local.date(), holidays),
            )
        if timeframe == "1D":
            return self.session_close(local.date(), holidays)
        if timeframe == "1W":
            week_start = local.date() - timedelta(days=local.weekday())
            days = [week_start + timedelta(days=offset) for offset in range(7)]
            trading_days = [day for day in days if self.is_trading_day(day, holidays)]
            if trading_days:
                last_day = trading_days[-1]
                return self.session_close(last_day, holidays)
        return timestamp
