"""
Instruments app - asset metadata, filtering, and option selection rules.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import (
    Exchange, InstrumentType, OptionType, StrikeSelectionLogic, 
    ExpiryType, ComparisonOperator, FyersSegment, ExchangeInstrumentType
)


class Instrument(BaseTimestampModel):
    """
    Trading instrument metadata synced from Fyers symbol master JSON.
    Covers equities, derivatives, currencies, and commodities.
    """
    # ── Identity ──
    fy_token = models.CharField(
        max_length=30, unique=True, db_index=True, default='',
        help_text="Fyers unique token (e.g. 101000000016921)"
    )
    exchange_token = models.IntegerField(
        default=0,
        help_text="Exchange-assigned token (exToken)"
    )
    symbol = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)
    sym_ticker = models.CharField(
        max_length=100, unique=True, default='',
        help_text="Full Fyers symbol (e.g. NSE:SBIN-EQ)"
    )
    short_name = models.CharField(max_length=50, blank=True, default='')
    display_name = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Mobile-friendly display name"
    )
    description = models.CharField(max_length=255, blank=True, default='')
    isin = models.CharField(max_length=20, blank=True, default='')

    # ── Classification ──
    exchange = models.CharField(max_length=20, choices=Exchange.choices)
    segment = models.IntegerField(
        choices=FyersSegment.choices, default=10,
        help_text="10=CM, 11=FO, 12=CD, 20=COM"
    )
    series = models.CharField(
        max_length=10, blank=True, default='',
        help_text="e.g. EQ, BE, FUT"
    )
    ex_inst_type = models.IntegerField(
        choices=ExchangeInstrumentType.choices, default=0,
        help_text="Exchange instrument type code"
    )
    instrument_type = models.CharField(
        max_length=20, choices=InstrumentType.choices,
        help_text="Derived from ex_inst_type during sync"
    )
    option_type = models.CharField(
        max_length=5, blank=True, default='XX',
        help_text="CE/PE/XX"
    )
    currency_code = models.CharField(max_length=5, default='INR')

    # ── Derivatives fields ──
    strike_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="-1 for non-options"
    )
    expiry_date = models.DateField(null=True, blank=True)
    underlying_symbol = models.CharField(max_length=50, blank=True, default='')
    underlying_fy_token = models.CharField(max_length=30, blank=True, default='')

    # ── Trading specifications ──
    lot_size = models.IntegerField(default=1)
    tick_size = models.DecimalField(max_digits=10, decimal_places=4, default=0.05)
    qty_freeze = models.IntegerField(
        null=True, blank=True,
        help_text="Freeze quantity limit"
    )
    qty_multiplier = models.DecimalField(
        max_digits=10, decimal_places=4, default=1.0
    )
    face_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    circuit_limit_upper = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    circuit_limit_lower = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    trading_session = models.CharField(
        max_length=100, blank=True, default='',
        help_text="e.g. 0915-1530|1815-1915:"
    )

    # ── Market data (updated daily via sync) ──
    previous_close = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    previous_oi = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    # ── MTF & Surveillance ──
    is_mtf_tradable = models.BooleanField(default=False)
    mtf_margin = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="MTF margin multiplier (e.g. 2.9x)"
    )
    asm_gsm_flag = models.CharField(
        max_length=100, blank=True, default='',
        help_text="ASM/GSM surveillance indicator"
    )

    # ── Availability flags ──
    has_options = models.BooleanField(default=False)
    has_futures = models.BooleanField(default=False)
    stream = models.CharField(max_length=20, blank=True, default='')

    # ── Status ──
    is_tradeable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_sync_date = models.DateField(
        null=True, blank=True,
        help_text="Fyers lastUpdate date"
    )

    class Meta:
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['sym_ticker']),
            models.Index(fields=['exchange', 'segment']),
            models.Index(fields=['exchange', 'instrument_type']),
            models.Index(fields=['underlying_symbol']),
            models.Index(fields=['isin']),
        ]

    def __str__(self):
        return f"{self.sym_ticker}"


class WatchlistInstrument(BaseTimestampModel):
    """
    Instruments added to a strategy's watchlist for trading.
    """
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='watchlist_instruments'
    )
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ['strategy', 'instrument']

    def __str__(self):
        return f"{self.strategy.name} - {self.instrument.symbol}"
