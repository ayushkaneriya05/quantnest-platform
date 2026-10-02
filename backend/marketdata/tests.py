from datetime import date, datetime, time
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from common.enums import OperandType
from .calendar import MarketSessionCalendar
from .access import StrategyMarketDataService


class MarketSessionCalendarTests(SimpleTestCase):
    def setUp(self):
        self.calendar = MarketSessionCalendar(
            "NSE", "Asia/Kolkata", time(9, 15), time(15, 30)
        )

    def test_intraday_bucket_origin_is_nse_open(self):
        origin = self.calendar.bucket_origin("5m").astimezone(ZoneInfo("Asia/Kolkata"))
        self.assertEqual((origin.weekday(), origin.hour, origin.minute), (0, 9, 15))

    def test_week_bucket_origin_is_monday_midnight(self):
        origin = self.calendar.bucket_origin("1W").astimezone(ZoneInfo("Asia/Kolkata"))
        self.assertEqual((origin.weekday(), origin.hour, origin.minute), (0, 0, 0))

    def test_minute_window_starts_at_exchange_open_and_excludes_full_holiday(self):
        zone = self.calendar.zone
        start = datetime(2026, 10, 5, 0, 0, tzinfo=zone)
        end = datetime(2026, 10, 6, 23, 59, tzinfo=zone)
        holiday = SimpleNamespace(is_partial=False, partial_close=None)
        expected = self.calendar.expected_1m_timestamps(
            start, end, {date(2026, 10, 6): holiday}
        )
        first = expected[0].astimezone(zone)
        last = expected[-1].astimezone(zone)
        self.assertEqual((first.hour, first.minute), (9, 15))
        self.assertEqual((last.date(), last.hour, last.minute), (date(2026, 10, 5), 15, 29))
        self.assertEqual(len(expected), 375)

    def test_weekly_availability_uses_actual_last_scheduled_session(self):
        friday_holiday = SimpleNamespace(is_partial=False, partial_close=None)
        week_start = datetime(2026, 10, 5, 0, 0, tzinfo=self.calendar.zone)
        close = self.calendar.candle_close(
            week_start, "1W", {date(2026, 10, 9): friday_holiday}
        )
        self.assertEqual(close, datetime(2026, 10, 8, 15, 30, tzinfo=self.calendar.zone))

    def test_warmup_starts_at_prior_session_and_skips_weekend(self):
        before = datetime(2026, 10, 12, 0, 0, tzinfo=self.calendar.zone)
        with patch.object(self.calendar, "load_holidays", return_value={}):
            warmup_start = self.calendar.warmup_start(before, 375)
        self.assertEqual(warmup_start, datetime(2026, 10, 9, 0, 0, tzinfo=self.calendar.zone))

    def test_warmup_skips_full_holiday_and_counts_partial_session_minutes(self):
        before = datetime(2026, 10, 12, 0, 0, tzinfo=self.calendar.zone)
        holidays = {
            date(2026, 10, 9): SimpleNamespace(is_partial=False, partial_close=None),
            date(2026, 10, 8): SimpleNamespace(is_partial=True, partial_close=time(13, 0)),
        }
        with patch.object(self.calendar, "load_holidays", return_value=holidays):
            warmup_start = self.calendar.warmup_start(before, 375)
        self.assertEqual(warmup_start, datetime(2026, 10, 7, 0, 0, tzinfo=self.calendar.zone))

    def test_weekly_warmup_starts_at_week_boundary(self):
        before = datetime(2026, 10, 12, 0, 0, tzinfo=self.calendar.zone)
        with patch.object(self.calendar, "load_holidays", return_value={}):
            warmup_start = self.calendar.warmup_start(before, 375, include_weekly=True)
        self.assertEqual(warmup_start, datetime(2026, 10, 5, 0, 0, tzinfo=self.calendar.zone))

    def test_instrument_exchange_selects_calendar_without_parsing_ticker(self):
        instrument = SimpleNamespace(exchange="BSE")
        with patch.object(MarketSessionCalendar, "for_exchange", return_value=self.calendar) as for_exchange:
            self.assertIs(MarketSessionCalendar.for_instrument(instrument), self.calendar)
        for_exchange.assert_called_once_with("BSE")

    def test_required_timeframes_includes_math_expression_variable_timeframe(self):
        config = {
            "time_rule": {"candle_timeframe": "1m"},
            "rule_groups": [{"rules": [{
                "operand_a_type": OperandType.MATH_EXPRESSION,
                "operand_a_params": {
                    "expression": {
                        "expression": "rsi_value",
                        "variables": {
                            "rsi_value": {
                                "type": OperandType.RSI,
                                "timeframe": "1W",
                                "params": {"period": 14},
                            }
                        },
                    }
                },
            }]}],
        }
        base_timeframe, required = StrategyMarketDataService.required_timeframes(config)
        self.assertEqual(base_timeframe, "1m")
        self.assertIn("1W", required)

    def test_partial_session_close_limits_expected_minutes(self):
        zone = self.calendar.zone
        start = datetime(2026, 10, 5, 0, 0, tzinfo=zone)
        end = datetime(2026, 10, 5, 23, 59, tzinfo=zone)
        partial_holiday = SimpleNamespace(is_partial=True, partial_close=time(13, 0))
        expected = self.calendar.expected_1m_timestamps(
            start, end, {date(2026, 10, 5): partial_holiday}
        )
        self.assertEqual(len(expected), 225)
        self.assertEqual(expected[-1].astimezone(zone).time(), time(12, 59))

    def test_coverage_counts_missing_valid_minute_candles(self):
        start = datetime(2026, 10, 5, 9, 15, tzinfo=self.calendar.zone)
        end = datetime(2026, 10, 5, 9, 17, tzinfo=self.calendar.zone)
        candle = {
            "time": int(datetime(2026, 10, 5, 9, 15, tzinfo=self.calendar.zone).timestamp()),
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
        }
        with patch.object(self.calendar, "load_holidays", return_value={}):
            coverage = self.calendar.coverage([candle], "1m", start, end)
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["missing_count"], 2)
        self.assertEqual(coverage["available_count"], 1)
