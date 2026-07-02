"""
Strategies app - core strategy configuration and metadata.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import (
    StrategyType, MarketType, Exchange, InstrumentType,
    StrategyStatus, StrategyVisibility, OrderType, QuantityType,
    LogicalOperator, EntryPriceLogic
)


class StrategyTag(models.Model):
    """
    Tags for categorizing strategies (trend, momentum, mean-reversion, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Strategy(BaseTimestampModel):
    """
    Core strategy configuration model.
    Contains all meta information about a trading strategy.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='strategies'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Strategy classification
    strategy_type = models.CharField(
        max_length=20,
        choices=StrategyType.choices,
        default=StrategyType.INTRADAY
    )
    market_type = models.CharField(
        max_length=20,
        choices=MarketType.choices,
        default=MarketType.EQUITY
    )
    exchange = models.CharField(
        max_length=20,
        choices=Exchange.choices,
        default=Exchange.NSE
    )
    instrument_type = models.CharField(
        max_length=20,
        choices=InstrumentType.choices,
        default=InstrumentType.STOCK
    )
    
    # Configuration
    auto_version_enabled = models.BooleanField(
        default=False,
        help_text="If true, versions are automatically created on save."
    )
    
    # Visibility and status
    visibility = models.CharField(
        max_length=20,
        choices=StrategyVisibility.choices,
        default=StrategyVisibility.PRIVATE
    )
    status = models.CharField(
        max_length=20,
        choices=StrategyStatus.choices,
        default=StrategyStatus.DRAFT
    )
    
    
    # Trading modes
    paper_trading_enabled = models.BooleanField(default=True)
    live_trading_enabled = models.BooleanField(default=False)
    
    # Sharing permissions
    allow_clone = models.BooleanField(default=False, help_text="Allow other users to clone this strategy")
    allow_backtest = models.BooleanField(default=False, help_text="Allow other users to backtest this strategy")
    
    # Tags
    tags = models.ManyToManyField(StrategyTag, blank=True, related_name='strategies')

    class Meta:
        verbose_name_plural = 'Strategies'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['visibility']),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def to_execution_dict(self):
        """
        Serializes the strategy and all its nested rules/configs into a single 
        JSON-serializable dictionary. This is used for caching in Redis to 
        avoid database hits during the live execution loop.
        """
        from strategies.services import StrategySnapshotService

        data = StrategySnapshotService._serialize_strategy(self)
        data.update(
            {
                "id": self.id,
                "user": self.user_id,
                "status": self.status,
                "visibility": self.visibility,
                "paper_trading_enabled": self.paper_trading_enabled,
                "live_trading_enabled": self.live_trading_enabled,
                "allow_backtest": self.allow_backtest,
            }
        )

        risk_profile = getattr(self.user, "risk_profile", None)
        if risk_profile:
            data["risk_profile"] = {
                "max_daily_loss_amount": float(risk_profile.max_daily_loss_amount) if risk_profile.max_daily_loss_amount is not None else None,
                "max_daily_loss_percentage": float(risk_profile.max_daily_loss_percentage),
                "max_exposure_percentage": float(risk_profile.max_exposure_percentage),
                "max_per_instrument_exposure": float(risk_profile.max_per_instrument_exposure),
                "max_drawdown_percentage": float(risk_profile.max_drawdown_percentage),
                "alert_on_breach": risk_profile.alert_on_breach,
            }
        else:
            data["risk_profile"] = {}

        return data

class StrategyVersion(BaseTimestampModel):
    """
    Version history for strategy configurations.
    Stores complete snapshots for rollback capability.
    """
    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    config_snapshot = models.JSONField(
        help_text="Complete strategy configuration at this version"
    )
    change_notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        unique_together = ['strategy', 'version_number']
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.strategy.name} v{self.version_number}"


class EntryOrderConfig(BaseTimestampModel):
    """
    Entry order configuration for a strategy.
    Defines how entry orders are placed.
    """
    strategy = models.OneToOneField(
        Strategy,
        on_delete=models.CASCADE,
        related_name='entry_order_config'
    )

    # Trade direction for this strategy
    entry_side = models.CharField(
        max_length=10,
        choices=[('BUY', 'Buy / Long'), ('SELL', 'Sell / Short')],
        default='BUY',
        help_text="Trade direction: BUY for Long entries, SELL for Short entries"
    )

    # Logic for combining rule groups
    entry_group_operator = models.CharField(
        max_length=10,
        choices=LogicalOperator.choices,
        default=LogicalOperator.OR,
        help_text="Logic for combining multiple entry groups (e.g., Group A OR Group B)"
    )
    
    # Order type
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.MARKET
    )
    
    # Entry price logic
    entry_price_logic = models.CharField(
        max_length=20,
        choices=EntryPriceLogic.choices,
        default=EntryPriceLogic.AT_CLOSE
    )
    price_offset = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text="Offset from signal price (positive for above, negative for below)"
    )
    
    allow_partial_entry = models.BooleanField(default=False)
    
    # Cooldown
    entry_cooldown_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Minimum seconds between entries"
    )

    def __str__(self):
        return f"{self.strategy.name} - Entry Config"


class ReEntryRule(BaseTimestampModel):
    """
    Re-entry rules after position exit.
    """
    strategy = models.OneToOneField(
        Strategy,
        on_delete=models.CASCADE,
        related_name='reentry_rule'
    )
    
    allow_reentry = models.BooleanField(default=True)
    max_reentries = models.PositiveIntegerField(
        default=2,
        help_text="Maximum re-entries per trading session"
    )
    reentry_cooldown_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Minimum seconds before re-entry"
    )
    
    # Reverse entry
    allow_reverse_entry = models.BooleanField(
        default=False,
        help_text="Allow reversing position on opposite signal"
    )
    
    # Loss recovery (Martingale-like)
    loss_recovery_mode = models.BooleanField(
        default=False,
        help_text="Increase position size after loss"
    )
    loss_recovery_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.5,
        help_text="Multiplier for position size after loss"
    )

    def __str__(self):
        return f"{self.strategy.name} - Re-entry Rules"


class ExitOrderConfig(BaseTimestampModel):
    strategy = models.OneToOneField(Strategy, on_delete=models.CASCADE, related_name='exit_order_config')
    # Logic for combining exit rule groups
    stop_loss_group_operator = models.CharField(
        max_length=10,
        choices=LogicalOperator.choices,
        default=LogicalOperator.OR,
        help_text="Logic for combining multiple stop loss groups"
    )
    
    target_group_operator = models.CharField(
        max_length=10,
        choices=LogicalOperator.choices,
        default=LogicalOperator.OR,
        help_text="Logic for combining multiple target groups"
    )

    def __str__(self):
        return f"{self.strategy.name} Exit Config"
