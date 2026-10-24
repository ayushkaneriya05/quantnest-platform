# backend/marketdata/models.py
from django.db import models
from common.encryption import EncryptedTextField
from django.utils import timezone

from common.models import BaseTimestampModel
from instruments.models import Instrument

class MarketDataToken(models.Model):
    """Singleton storing the market-data access token from admin sign-in."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    access_token = EncryptedTextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True,)  # UTC
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True) # Added active field

    class Meta:
        verbose_name = "Market Data Token"
        verbose_name_plural = "Market Data Tokens"

    def is_valid(self):
        if not self.is_active or not self.access_token:
            return False
        if self.expires_at is None:
            return False
        return timezone.now() < self.expires_at

    @classmethod
    def active_access_token(cls):
        """Read the valid source credential; expired tokens need admin sign-in."""
        token = cls.objects.filter(pk=1).first()
        return token.access_token if token and token.is_valid() else None

    def __str__(self):
        return f"MarketDataToken(valid={self.is_valid()}, expires_at={self.expires_at})"


class HistoryCoverage(models.Model):
    """Successfully acquired ranges. Empty results do not prove there were no trades."""
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    provider = models.CharField(max_length=100, default="fyers")
    timeframe = models.CharField(max_length=2)
    start = models.DateTimeField()
    end = models.DateTimeField()
    checked_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['instrument', 'provider', 'timeframe', 'start'], name='history_coverage_source')]
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F('start')), name='history_coverage_forward')]


class Candle(BaseTimestampModel):
    """
    TimescaleDB-backed historical candle store.

    In production this model should map to a Timescale hypertable with
    compression and indexes applied at the database layer.
    """

    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candles",
    )
    symbol = models.CharField(max_length=100, db_index=True)
    provider = models.CharField(max_length=100, default="fyers")
    timeframe = models.CharField(max_length=10, db_index=True, default="1m")
    time = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=18, decimal_places=6)
    high = models.DecimalField(max_digits=18, decimal_places=6)
    low = models.DecimalField(max_digits=18, decimal_places=6)
    close = models.DecimalField(max_digits=18, decimal_places=6)
    volume = models.BigIntegerField(default=0)
    provider_confirmed = models.BooleanField(default=False, db_default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["symbol", "provider", "timeframe", "time"],
                name="unique_candle_provider_time",
            )
        ]
        indexes = [
            models.Index(fields=["symbol", "provider", "timeframe", "-time"], name="candle_source_time"),
            models.Index(fields=["timeframe", "-time"]),
        ]
        ordering = ["time"]

    def __str__(self):
        return f"{self.symbol} {self.timeframe} {self.time.isoformat()}"
