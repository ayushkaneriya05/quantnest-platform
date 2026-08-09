"""
Common app - base models for QuantNest Algo Trading Platform.
"""
from django.db import models


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
    EXCHANGE_CHOICES = [
        ('NSE', 'National Stock Exchange'),
        ('BSE', 'Bombay Stock Exchange'),
        ('NFO', 'NSE Futures & Options'),
        ('MCX', 'Multi Commodity Exchange'),
        ('CDS', 'Currency Derivatives'),
        ('BFO', 'BSE Futures & Options'),
    ]

    exchange = models.CharField(
        max_length=10,
        choices=EXCHANGE_CHOICES,
        unique=True,
        help_text='Exchange identifier (e.g., NSE, BSE, MCX)'
    )
    market_open = models.TimeField(
        help_text='Regular market open time (e.g., 09:15 for NSE)'
    )
    market_close = models.TimeField(
        help_text='Regular market close time (e.g., 15:30 for NSE)'
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
        ordering = ['exchange']
        verbose_name = 'Exchange Configuration'
        verbose_name_plural = 'Exchange Configurations'

    def __str__(self):
        return f"{self.get_exchange_display()} ({self.market_open} - {self.market_close})"


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

    class Meta:
        db_table = 'market_holidays'
        ordering = ['-date']
        unique_together = ['exchange', 'date']
        verbose_name = 'Market Holiday'
        verbose_name_plural = 'Market Holidays'

    def __str__(self):
        return f"{self.exchange.exchange} - {self.date} - {self.description}"
