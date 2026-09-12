from django.db import models
from django.utils import timezone

from common.enums import Severity
from common.models import BaseTimestampModel
from instruments.models import Instrument

# Canonical timeframes physically stored in the DB.
CANONICAL_TIMEFRAMES = frozenset({"1m", "1D"})


class MarketDataToken(models.Model):
    """
    Singleton row (pk=1) for the Fyers market-data access token.
    Use get_or_create(pk=1) to read/write.
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_type = models.CharField(max_length=32, default="Bearer", blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # UTC
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Market Data Token"
        verbose_name_plural = "Market Data Tokens"

    def is_valid(self):
        if not self.access_token:
            return False
        if self.expires_at is None:
            return False
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"MarketDataToken(valid={self.is_valid()}, expires_at={self.expires_at})"


class MarketEvent(BaseTimestampModel):
    EVENT_TYPE_CHOICES = [
        ("EARNINGS", "Earnings"),
        ("RBI_POLICY", "RBI Policy"),
        ("BUDGET", "Union Budget"),
        ("GDP", "GDP Data"),
        ("INFLATION", "Inflation Data"),
        ("FED_DECISION", "Fed Decision"),
        ("NEWS", "News Event"),
        ("CUSTOM", "Custom Event"),
        # Exchange non-trading days used by TradingCalendar for gap detection
        ("NSE_HOLIDAY", "NSE Holiday"),
    ]

    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="market_events",
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    impact = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)
    source = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["event_date", "event_time", "title"]
        indexes = [
            models.Index(fields=["event_type", "event_date"]),
            models.Index(fields=["event_date"]),
        ]

    def __str__(self):
        instrument = self.instrument.symbol if self.instrument else "Market"
        return f"{self.event_type} - {instrument} - {self.event_date}"


class Candle(BaseTimestampModel):
    """
    TimescaleDB-backed historical candle store.

    Only CANONICAL timeframes (1m, 1D) are stored here.
    All higher timeframes (3m, 5m, 15m, 30m, 1H, 4H, 1W) are derived on demand.

    Identity: (symbol, timeframe, time) for fast symbol-string queries.
    The instrument FK is preserved for analytics/backtest joins.

    In production this table should be a Timescale hypertable with
    compression and chunk indexes applied at the database layer.
    """
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candles",
    )
    symbol = models.CharField(max_length=100, db_index=True)
    timeframe = models.CharField(max_length=10, db_index=True, default="1m")
    time = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=18, decimal_places=6)
    high = models.DecimalField(max_digits=18, decimal_places=6)
    low = models.DecimalField(max_digits=18, decimal_places=6)
    close = models.DecimalField(max_digits=18, decimal_places=6)
    volume = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["symbol", "timeframe", "time"],
                name="unique_candle_symbol_timeframe_time",
            )
        ]
        indexes = [
            models.Index(fields=["symbol", "timeframe", "-time"]),
            models.Index(fields=["timeframe", "-time"]),
            models.Index(
                fields=["instrument", "timeframe", "-time"],
                name="candle_instrument_tf_time_idx",
            ),
        ]
        ordering = ["time"]

    def __str__(self):
        return f"{self.symbol} {self.timeframe} {self.time.isoformat()}"
