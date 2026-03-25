"""
Risk Management Models

Handles position sizing rules, portfolio risk profiles, trade halt conditions,
strategy auto-disable rules, and risk violation logging.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import (
    QuantityType, HaltConditionType, AutoDisableTriggerType,
    ViolationType, ViolationAction, Severity
)


class PositionSizingRule(BaseTimestampModel):
    """
    Defines how position size is calculated for a strategy.
    Supports fixed quantity, capital-based, and risk-based sizing.
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
    
    # Risk-based sizing
    risk_per_trade_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Fixed rupee amount to risk per trade"
    )
    risk_per_trade_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00, null=True, blank=True,
        help_text="Percentage of capital to risk per trade"
    )
    
    # Strategy Limits
    max_daily_trades = models.PositiveIntegerField(
        default=10,
        help_text="Maximum number of trades per day for this strategy"
    )
    max_open_positions = models.PositiveIntegerField(
        default=5,
        help_text="Maximum concurrent open positions for this strategy"
    )
    
    class Meta:
        db_table = 'risk_position_sizing_rule'
        verbose_name = 'Position Sizing Rule'
        verbose_name_plural = 'Position Sizing Rules'

    def __str__(self):
        return f"Sizing for {self.strategy.name}"


class PortfolioRiskProfile(BaseTimestampModel):
    """
    Portfolio-level risk limits and controls.
    Applied across all strategies for a user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='risk_profile'
    )
    
    # Daily limits
    max_daily_loss_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Maximum daily loss in rupees"
    )
    max_daily_loss_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text="Maximum daily loss as % of capital"
    )
    max_daily_trades = models.PositiveIntegerField(
        default=50,
        help_text="Maximum trades per day across all strategies"
    )
    
    # Position limits
    max_open_positions = models.PositiveIntegerField(
        default=10,
        help_text="Maximum concurrent open positions"
    )
    max_exposure_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=80.00,
        help_text="Maximum portfolio exposure as % of capital"
    )
    
    # Per-strategy limits
    max_per_strategy_allocation = models.DecimalField(
        max_digits=5, decimal_places=2, default=25.00,
        help_text="Maximum capital allocated to a single strategy"
    )
    
    # Per-instrument limits
    max_per_instrument_exposure = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        help_text="Maximum exposure to a single instrument"
    )
    
    # Drawdown controls
    max_drawdown_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00,
        help_text="Maximum portfolio drawdown before halt"
    )
    trailing_drawdown_reset = models.BooleanField(
        default=True,
        help_text="Reset drawdown counter on new high"
    )
    
    # Notifications
    alert_on_breach = models.BooleanField(default=True)
    halt_on_breach = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'risk_portfolio_profile'
        verbose_name = 'Portfolio Risk Profile'
        verbose_name_plural = 'Portfolio Risk Profiles'

    def __str__(self):
        return f"Risk Profile for {self.user.username}"


class TradeHaltCondition(BaseTimestampModel):
    """
    Conditions that trigger a trading halt.
    Can be global or strategy-specific.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='halt_conditions'
    )

    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Condition type
    condition_type = models.CharField(
        max_length=20,
        choices=HaltConditionType.choices
    )
    
    # Threshold values
    threshold_value = models.DecimalField(
        max_digits=15, decimal_places=4, default=0, null=True, blank=True
    )
    threshold_count = models.PositiveIntegerField(default=0, null=True, blank=True)
    
    # Actions
    halt_duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Duration of halt in minutes (0 = until EOD)"
    )
    close_open_positions = models.BooleanField(
        default=False,
        help_text="Close all positions when halt triggered"
    )
    send_notification = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'risk_halt_condition'
        verbose_name = 'Trade Halt Condition'
        verbose_name_plural = 'Trade Halt Conditions'

    def __str__(self):
        return f"{self.name} (Portfolio)"


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
        choices=AutoDisableTriggerType.choices
    )
    
    # Thresholds
    threshold_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    threshold_count = models.PositiveIntegerField(default=0, null=True, blank=True)
    
    # Recovery
    auto_reenable = models.BooleanField(
        default=False,
        help_text="Automatically re-enable after cooldown"
    )
    cooldown_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before auto re-enable"
    )
    require_manual_review = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'risk_strategy_auto_disable'
        verbose_name = 'Strategy Auto-Disable Rule'
        verbose_name_plural = 'Strategy Auto-Disable Rules'

    def __str__(self):
        return f"{self.name} for {self.strategy.name}"


class RiskViolation(BaseTimestampModel):
    """
    Log of risk rule violations and actions taken.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='risk_violations'
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='risk_violations'
    )
    
    # Violation details
    violation_type = models.CharField(
        max_length=20,
        choices=ViolationType.choices
    )
    
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.WARNING
    )
    
    message = models.TextField()
    threshold_value = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    actual_value = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    
    # Action taken
    action_taken = models.CharField(
        max_length=20,
        choices=ViolationAction.choices
    )
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_violations'
    )
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'risk_violation'
        verbose_name = 'Risk Violation'
        verbose_name_plural = 'Risk Violations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.violation_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
