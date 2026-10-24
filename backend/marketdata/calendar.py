"""One exchange/segment calendar for ingestion, charts and execution."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from common.enums import FyersSegment
from .contracts import interval_minutes


class MarketSessionCalendar:
    def __init__(self, exchange, timezone_name, market_open, market_close, *,
                 segment=FyersSegment.CAPITAL_MARKET, config_id=None,
                 trading_weekdays=(0, 1, 2, 3, 4), session_breaks=()):
        self.exchange, self.segment, self.config_id = exchange, segment, config_id
        self.timezone_name, self.zone = timezone_name, ZoneInfo(timezone_name)
        self.market_open, self.market_close = market_open, market_close
        self.trading_weekdays = frozenset(trading_weekdays)
        self.session_breaks = tuple((time.fromisoformat(left), time.fromisoformat(right))
                                    for left, right in session_breaks)
        self._holidays, self._periods, self._loaded_holiday_ranges = {}, {}, []

    @property
    def signature(self):
        return (self.timezone_name, self.market_open, self.market_close, tuple(sorted(self.trading_weekdays)),
                self.session_breaks, tuple((day, row.is_partial, row.partial_open, row.partial_close)
                                          for day, row in sorted(self._holidays.items())))

    @classmethod
    def for_instrument(cls, instrument):
        return cls.for_exchange(instrument.exchange, instrument.segment)

    @classmethod
    def for_exchange(cls, exchange, segment=FyersSegment.CAPITAL_MARKET):
        from common.models import ExchangeConfig
        config = ExchangeConfig.objects.filter(exchange=exchange, segment=segment, is_active=True).first()
        if config is None:
            raise ValueError(f"Configure an active calendar for {exchange} segment {segment}.")
        return cls(exchange, config.timezone, config.market_open, config.market_close,
                   segment=segment, config_id=config.pk, trading_weekdays=config.trading_weekdays,
                   session_breaks=config.session_breaks)

    @classmethod
    def for_symbol(cls, symbol):
        from instruments.models import Instrument
        return cls.for_instrument(Instrument.objects.get(sym_ticker=symbol))

    def load_holidays(self, start_date, end_date):
        from common.models import MarketHoliday
        if any(start <= start_date and end_date <= end for start, end in self._loaded_holiday_ranges):
            return self._holidays
        rows = MarketHoliday.objects.filter(exchange_id=self.config_id, date__gte=start_date, date__lte=end_date)
        self._holidays.update({row.date: row for row in rows})
        self._loaded_holiday_ranges.append((start_date, end_date))
        self._periods.clear()
        return self._holidays

    def is_trading_day(self, day):
        holiday = self._holidays.get(day)
        return holiday.is_partial if holiday is not None else day.weekday() in self.trading_weekdays

    def session_open(self, day):
        holiday = self._holidays.get(day)
        opening = holiday.partial_open if holiday and holiday.is_partial and holiday.partial_open else self.market_open
        return datetime.combine(day, opening, self.zone)

    def session_close(self, day):
        holiday = self._holidays.get(day)
        clock = holiday.partial_close if holiday and holiday.is_partial and holiday.partial_close else self.market_close
        closing = datetime.combine(day, clock, self.zone)
        return closing + timedelta(days=1) if closing <= self.session_open(day) else closing

    def trading_periods(self, day):
        """Continuous trading periods; intraday buckets restart after each break."""
        if day not in self._periods:
            periods = []
            if self.is_trading_day(day):
                opening, closing = self.session_open(day), self.session_close(day)
                cursor = opening
                regular_open = datetime.combine(day, self.market_open, self.zone)
                for start, end in self.session_breaks:
                    left, right = datetime.combine(day, start, self.zone), datetime.combine(day, end, self.zone)
                    if left < regular_open:
                        left += timedelta(days=1)
                    if right <= left:
                        right += timedelta(days=1)
                    left, right = max(opening, left), min(closing, right)
                    if left >= right:
                        continue
                    if cursor < left:
                        periods.append((cursor, left))
                    cursor = max(cursor, right)
                if cursor < closing:
                    periods.append((cursor, closing))
            self._periods[day] = tuple(periods)
        return self._periods[day]

    @property
    def session_minutes(self):
        # Coarse sizing only; actual windows use dated session periods.
        opening = datetime.combine(date.min, self.market_open)
        closing = datetime.combine(date.min, self.market_close)
        minutes = int((closing - opening).total_seconds() // 60)
        return minutes if minutes > 0 else minutes + 1440

    def session_bounds(self, instant):
        local = instant.astimezone(self.zone)
        day = local.date()
        previous_close = self.session_close(day - timedelta(days=1))
        if previous_close.date() == day and local < previous_close:
            day -= timedelta(days=1)
        return self.session_open(day), self.session_close(day)

    def is_open(self, instant):
        day = self.session_bounds(instant)[0].date()
        return any(left <= instant < right for left, right in self.trading_periods(day))

    def require_open(self, instant):
        day = instant.astimezone(self.zone).date()
        self.load_holidays(day - timedelta(days=1), day + timedelta(days=1))
        if not self.is_open(instant):
            raise ValueError(f"{self.exchange} {self.segment} is closed. Orders are accepted during its configured trading session.")

    def bucket_start(self, instant, timeframe):
        day = self.session_bounds(instant)[0].date()
        if timeframe == "1W":
            return datetime.combine(day - timedelta(days=day.weekday()), time.min, self.zone)
        if timeframe == "1M":
            return datetime.combine(day.replace(day=1), time.min, self.zone)
        if timeframe == "1D":
            return self.session_open(day)
        opening = next((left for left, right in self.trading_periods(day) if left <= instant < right),
                       self.session_open(day))
        step = interval_minutes(timeframe) * 60
        stamp = opening.timestamp() + ((instant.timestamp() - opening.timestamp()) // step) * step
        return datetime.fromtimestamp(stamp, self.zone)

    def candle_close(self, timestamp, timeframe):
        local = timestamp.astimezone(self.zone)
        minutes = interval_minutes(timeframe)
        if minutes is not None:
            day = self.session_bounds(local)[0].date()
            closing = next((right for left, right in self.trading_periods(day) if left <= local < right),
                           self.session_close(day))
            return min(datetime.fromtimestamp(local.timestamp() + minutes * 60, self.zone), closing)
        if timeframe == "1D":
            return self.session_close(local.date())
        first = local.date()
        end = (first - timedelta(days=first.weekday()) + timedelta(days=7) if timeframe == "1W" else
               (first.replace(day=28) + timedelta(days=4)).replace(day=1))
        day = end - timedelta(days=1)
        while day >= first and not self.is_trading_day(day):
            day -= timedelta(days=1)
        return self.session_close(day) if day >= first else timestamp

    def completed_horizon(self, timeframe, as_of):
        """Pure lookup against an already loaded calendar; safe in calculations."""
        day = self.session_bounds(as_of)[0].date()
        minutes = interval_minutes(timeframe)
        for _ in range(370):
            if self.is_trading_day(day):
                if minutes is not None:
                    for left, right in reversed(self.trading_periods(day)):
                        if right <= as_of:
                            return right.timestamp()
                        if left < as_of:
                            step = minutes * 60
                            return left.timestamp() + ((as_of.timestamp() - left.timestamp()) // step) * step
                else:
                    start = self.bucket_start(self.session_open(day), timeframe)
                    closing = self.candle_close(start, timeframe)
                    if closing <= as_of:
                        return closing.timestamp()
            day -= timedelta(days=1)
        raise ValueError("No completed session exists in the loaded calendar.")

    def warmup_start(self, before, count, *, source="1m", include_weekly=False):
        """Count dated source slots, independently for minute and daily history."""
        day = self.session_bounds(before)[0].date() - timedelta(days=1)
        remaining, loaded_start = max(0, count), day + timedelta(days=1)
        while remaining:
            if day < loaded_start:
                loaded_start = day - timedelta(days=31)
                self.load_holidays(loaded_start, day)
            if self.is_trading_day(day):
                remaining -= (1 if source == "1D" else sum(
                    int((right.timestamp() - left.timestamp()) // 60) for left, right in self.trading_periods(day)))
                if remaining <= 0:
                    break
            day -= timedelta(days=1)
        if include_weekly:
            day -= timedelta(days=day.weekday())
        return datetime.combine(day, time.min, self.zone)

    def source_count(self, source, start, end):
        count = 0
        first = self.session_bounds(start)[0].date()
        for day in self._date_range(first, end.astimezone(self.zone).date()):
            if source == "1D":
                count += int(self.is_trading_day(day) and start <= self.session_open(day) < end
                             and self.session_close(day) <= end)
            else:
                for left, right in self.trading_periods(day):
                    count += max(0, int((min(right, end).timestamp() - max(left, start).timestamp()) // 60))
        return count

    @staticmethod
    def _date_range(start_date, end_date):
        while start_date <= end_date:
            yield start_date
            start_date += timedelta(days=1)
