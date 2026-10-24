"""
Common app - base models for QuantNest Algo Trading Platform.
"""
from django.db import models

from common.enums import Exchange, FyersSegment, Timezone


def trading_weekdays():
    return [0, 1, 2, 3, 4]


class BaseTimestampModel(models.Model):
    """Abstract base model with timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True






class ExchangeConfig(BaseTimestampModel):
    """Stores market timing configuration for each exchange.

    Eliminates hardcoded market hours across the platform by providing
    a single source of truth for exchange trading schedules.
    """
    exchange = models.CharField(
        max_length=10,
        choices=Exchange.choices,
        help_text='Exchange identifier (e.g., NSE, BSE, MCX)'
    )
    segment = models.PositiveSmallIntegerField(
        choices=FyersSegment.choices,
        default=FyersSegment.CAPITAL_MARKET,
    )
    market_open = models.TimeField(
        help_text='Regular market open time (e.g., 09:15 for NSE)'
    )
    market_close = models.TimeField(
        help_text='Regular market close time (e.g., 15:30 for NSE)'
    )
    trading_weekdays = models.JSONField(default=trading_weekdays,
        help_text='Trading weekdays: Monday=0 through Sunday=6.')
    session_breaks = models.JSONField(default=list, blank=True,
        help_text='Local session breaks, e.g. [["12:00", "13:00"]]. Leave [] for continuous trading.')
    timezone = models.CharField(
        max_length=64,
        choices=Timezone.choices,
        default=Timezone.ASIA_KOLKATA,
        help_text='IANA timezone used for exchange sessions (e.g., Asia/Kolkata)',
    )
    pre_market_open = models.TimeField(
        null=True,
        blank=True,
        help_text='Pre-market session open time'
    )
    pre_market_close = models.TimeField(
        null=True,
        blank=True,
        help_text='Pre-market session close time'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this exchange is currently active'
    )

    class Meta:
        db_table = 'exchange_configs'
        ordering = ['exchange', 'segment']
        constraints = [models.UniqueConstraint(fields=['exchange', 'segment'], name='unique_exchange_segment')]
        verbose_name = 'Exchange Configuration'
        verbose_name_plural = 'Exchange Configurations'

    def __str__(self):
        return f"{self.exchange} · {self.get_segment_display()} ({self.market_open} - {self.market_close})"

    def clean(self):
        from datetime import date, datetime, time, timedelta

        from django.core.exceptions import ValidationError
        if (not isinstance(self.trading_weekdays, list) or not self.trading_weekdays
                or any(type(day) is not int or day not in range(7) for day in self.trading_weekdays)
                or len(set(self.trading_weekdays)) != len(self.trading_weekdays)):
            raise ValidationError({"trading_weekdays": "Use distinct weekday numbers from 0 to 6."})
        if not isinstance(self.session_breaks, list):
            raise ValidationError({"session_breaks": "Use a list of [start, end] local times."})
        opening = datetime.combine(date(2000, 1, 1), self.market_open)
        closing = datetime.combine(opening.date(), self.market_close)
        if closing <= opening:
            closing += timedelta(days=1)
        previous = opening
        for value in self.session_breaks:
            try:
                if not isinstance(value, list) or len(value) != 2:
                    raise ValueError
                left, right = [datetime.combine(opening.date(), time.fromisoformat(item)) for item in value]
                if left < opening:
                    left += timedelta(days=1)
                if right <= left:
                    right += timedelta(days=1)
                if not previous <= left < right <= closing:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({"session_breaks": "Use ordered, non-overlapping [HH:MM, HH:MM] breaks within the session."}) from None
            previous = right


class MarketHoliday(BaseTimestampModel):
    """Tracks market holidays for each exchange.

    Used to skip signal evaluation on non-trading days and
    to calculate accurate trading day counts for analytics.
    """
    exchange = models.ForeignKey(
        ExchangeConfig,
        on_delete=models.CASCADE,
        related_name='holidays',
        help_text='Exchange this holiday applies to'
    )
    date = models.DateField(
        help_text='Holiday date'
    )
    description = models.CharField(
        max_length=200,
        help_text='Holiday name/description (e.g., "Republic Day", "Diwali")'
    )
    is_partial = models.BooleanField(
        default=False,
        help_text='If True, market has shortened hours on this date'
    )
    partial_close = models.TimeField(
        null=True,
        blank=True,
        help_text='Early close time for partial trading days'
    )
    partial_open = models.TimeField(null=True, blank=True, help_text='Opening time for a special session, including weekend trading')

    class Meta:
        db_table = 'market_holidays'
        ordering = ['-date']
        unique_together = ['exchange', 'date']
        verbose_name = 'Market Holiday'
        verbose_name_plural = 'Market Holidays'

    def __str__(self):
        return f"{self.exchange.exchange} - {self.date} - {self.description}"
