"""
Strategies app - core strategy configuration and metadata.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from .definitions import default_definition
from .specification.configuration import DETAIL_FIELDS
from common.enums import (
    StrategyType, MarketType, Exchange, InstrumentType,
    StrategyStatus, StrategyVisibility
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

    # One executable document, copied into immutable versions at save time.
    definition = models.JSONField(default=default_definition, editable=False)

    # Strategy classification
    strategy_type = models.CharField(
        max_length=20,
        choices=StrategyType.choices,
        default=DETAIL_FIELDS['strategy_type']['default']
    )
    market_type = models.CharField(
        max_length=20,
        choices=MarketType.choices,
        default=DETAIL_FIELDS['market_type']['default']
    )
    exchange = models.CharField(
        max_length=20,
        choices=Exchange.choices,
        default=DETAIL_FIELDS['exchange']['default']
    )
    instrument_type = models.CharField(
        max_length=20,
        choices=InstrumentType.choices,
        default=DETAIL_FIELDS['instrument_type']['default']
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
        default=DETAIL_FIELDS['visibility']['default']
    )
    status = models.CharField(
        max_length=20,
        choices=StrategyStatus.choices,
        default=DETAIL_FIELDS['status']['default']
    )


    # Trading modes
    paper_trading_enabled = models.BooleanField(default=DETAIL_FIELDS['paper_trading_enabled']['default'])
    live_trading_enabled = models.BooleanField(default=DETAIL_FIELDS['live_trading_enabled']['default'])

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
            }
        )

        return data

    def delete(self, *args, **kwargs):
        """Prevent deletion of strategies with associated trading data.

        Strategies with any historical data (backtests, paper trades, live sessions)
        must be archived instead of deleted to preserve audit trails.
        """
        from django.core.exceptions import ValidationError

        has_paper = (
            self.capital_allocations.exists()
            or self.paper_positions.exists()
            or self.paper_orders.exists()
            or self.paper_trades.exists()
        )
        has_live = (
            self.live_sessions.exists()
            or self.live_allocations.exists()
            or self.live_positions.exists()
            or self.live_orders.exists()
        )
        has_backtest = self.backtest_runs.exists()

        if has_paper or has_live or has_backtest:
            parts = []
            if has_paper:
                parts.append('paper trading data')
            if has_live:
                parts.append('live trading sessions')
            if has_backtest:
                parts.append('backtest runs')
            raise ValidationError(
                f"Cannot delete strategy '{self.name}': has {', '.join(parts)}. "
                f"Archive the strategy instead."
            )

        super().delete(*args, **kwargs)

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
