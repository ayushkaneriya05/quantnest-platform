"""
Risk Management Models

Handles position sizing rules and strategy auto-disable rules.
"""
from django.db import models
from common.models import BaseTimestampModel
from common.enums import QuantityType, AutoDisableTriggerType


class PositionSizingRule(BaseTimestampModel):
    """
    Defines how position size is calculated for a strategy.
    Supports fixed quantity and capital-based sizing.
    """
    strategy = models.OneToOneField(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='position_sizing_rule'
    )
    
    # Sizing method
    sizing_method = models.CharField(
        max_length=20,
        choices=QuantityType.choices,
        default=QuantityType.CAPITAL_BASED
    )
    
    # Fixed sizing
    fixed_quantity = models.PositiveIntegerField(default=1, null=True, blank=True)
    
    # Capital-based sizing
    capital_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00, null=True, blank=True,
        help_text="Percentage of capital per trade"
    )
    
    
    class Meta:
        db_table = 'risk_position_sizing_rule'
        verbose_name = 'Position Sizing Rule'
        verbose_name_plural = 'Position Sizing Rules'

    def __str__(self):
        return f"Sizing for {self.strategy.name}"


class StrategyAutoDisable(BaseTimestampModel):
    """
    Rules for automatically disabling strategies based on performance.
    """
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='auto_disable_rules'
    )
    
    name = models.CharField(max_length=100)
    
    # Trigger conditions
    trigger_type = models.CharField(
        max_length=20,
        choices=AutoDisableTriggerType.choices,
        default=AutoDisableTriggerType.CONSECUTIVE_LOSSES,
    )
    
    # Thresholds
    threshold_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    threshold_count = models.PositiveIntegerField(default=5, null=True, blank=True)
    
    # Recovery
    auto_reenable = models.BooleanField(
        default=False,
        help_text="Automatically re-enable after cooldown"
    )
    cooldown_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before auto re-enable"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'risk_strategy_auto_disable'
        verbose_name = 'Strategy Auto-Disable Rule'
        verbose_name_plural = 'Strategy Auto-Disable Rules'

    def __str__(self):
        return f"{self.name} for {self.strategy.name}"


