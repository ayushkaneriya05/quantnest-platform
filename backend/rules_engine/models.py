"""
Rules Engine app - trading rules, signals, time filters, stop loss, and targets.
"""
from django.db import models
from common.models import BaseTimestampModel
from common.enums import (
    CandleTimeframe, CandleCompletionRule, MarketSession, LogicalOperator,
    RuleType, RuleCategory, IndicatorType, PriceActionType, VolumeConditionType,
    ComparisonOperator, StopLossType, TargetType, CandlePart, Timezone
)


class TimeRule(BaseTimestampModel):
    """
    Time and session rules for strategy execution.
    Defines when the strategy is allowed to trade.
    """
    strategy = models.OneToOneField(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='time_rule'
    )
    
    # Trading days (JSON array of weekday names)
    trading_days = models.JSONField(
        default=list,
        help_text="List of trading days: ['Monday', 'Tuesday', ...]"
    )
    
    # Market session
    market_session = models.CharField(
        max_length=20,
        choices=MarketSession.choices,
        default=MarketSession.ALL
    )
    
    # Time window
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for trading (IST)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for trading (IST)"
    )
    
    # Candle settings
    candle_timeframe = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        default=CandleTimeframe.M5
    )
    candle_completion_rule = models.CharField(
        max_length=20,
        choices=CandleCompletionRule.choices,
        default=CandleCompletionRule.ON_CLOSE
    )
    
    # No-trade windows (JSON array of {start, end} objects)
    no_trade_windows = models.JSONField(
        null=True,
        blank=True,
        help_text="Time windows to avoid: [{start: '13:00', end: '14:00'}, ...]"
    )
    
    timezone = models.CharField(
        max_length=50, 
        choices=Timezone.choices,
        default=Timezone.ASIA_KOLKATA
    )

    def __str__(self):
        return f"{self.strategy.name} - Time Rules"


class SpecialEventFilter(BaseTimestampModel):
    """
    Filters to avoid trading during special market events.
    """
    strategy = models.OneToOneField(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='special_event_filter'
    )
    
    avoid_earnings = models.BooleanField(
        default=False,
        help_text="Avoid trading on earnings announcement days"
    )
    avoid_news = models.BooleanField(
        default=False,
        help_text="Avoid trading during major news events"
    )
    avoid_expiry_day = models.BooleanField(
        default=True,
        help_text="Avoid trading on F&O expiry days"
    )
    avoid_rbi_policy = models.BooleanField(
        default=False,
        help_text="Avoid trading on RBI policy days"
    )
    custom_avoid_dates = models.JSONField(
        null=True,
        blank=True,
        help_text="Custom dates to avoid trading: ['2024-01-26', ...]"
    )

    def __str__(self):
        return f"{self.strategy.name} - Event Filters"


class RuleGroup(BaseTimestampModel):
    """
    Group of rules combined with logical operators.
    Supports AND/OR logic, sequential conditions, and minimum confirmations.
    """
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='rule_groups'
    )
    name = models.CharField(max_length=100, blank=True)
    rule_type = models.CharField(
        max_length=20,
        choices=RuleType.choices,
        default=RuleType.ENTRY
    )
    logical_operator = models.CharField(
        max_length=10,
        choices=LogicalOperator.choices,
        default=LogicalOperator.AND
    )
    priority = models.PositiveIntegerField(
        default=1,
        help_text="Evaluation priority (lower = higher priority)"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['rule_type', 'priority']

    def __str__(self):
        return f"{self.strategy.name} - {self.rule_type} Group ({self.logical_operator})"


class Rule(BaseTimestampModel):
    """
    Individual trading rule/condition.
    Can be indicator-based, price action, or volume-based.
    """
    rule_group = models.ForeignKey(
        RuleGroup,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    
    # Rule classification
    category = models.CharField(
        max_length=20,
        choices=RuleCategory.choices,
        default=RuleCategory.INDICATOR
    )
    
    # For indicator-based rules
    indicator_type = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True
    )
    
    # For price action rules
    price_action_type = models.CharField(
        max_length=30,
        choices=PriceActionType.choices,
        null=True,
        blank=True
    )
    
    # For volume rules
    volume_condition_type = models.CharField(
        max_length=30,
        choices=VolumeConditionType.choices,
        null=True,
        blank=True
    )
    
    # Parameters (JSON for flexibility)
    params = models.JSONField(
        null=True,
        blank=True,
        help_text="Indicator parameters: {period: 14, source: 'close', ...}"
    )
    
    # Comparison
    comparison = models.CharField(
        max_length=20,
        choices=ComparisonOperator.choices,
        default=ComparisonOperator.GREATER
    )
    value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Comparison value"
    )
    value2 = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Second value for BETWEEN comparisons"
    )
    
    # Compare to another indicator (for crossovers)
    compare_to_indicator = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True,
        help_text="Compare to another indicator (for crossovers)"
    )
    compare_to_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Parameters for comparison indicator"
    )
    
    # Timeframe override
    timeframe_override = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        null=True,
        blank=True,
        help_text="Use different timeframe for this rule"
    )
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        if self.indicator_type:
            return f"{self.indicator_type} {self.comparison} {self.value}"
        elif self.price_action_type:
            return f"{self.price_action_type}"
        elif self.volume_condition_type:
            return f"{self.volume_condition_type}"
        return f"Rule {self.id}"


class StopLossRule(BaseTimestampModel):
    """
    Stop loss configuration for a strategy.
    Supports multiple SL types: fixed, ATR, trailing, time-based, etc.
    """
    rule_group = models.ForeignKey(
        RuleGroup,
        on_delete=models.CASCADE,
        related_name='stop_loss_rules',
        null=True, blank=True
    )
    sl_type = models.CharField(
        max_length=30,
        choices=StopLossType.choices,
        default=StopLossType.FIXED_PERCENTAGE
    )
    
    # Fixed stops
    fixed_points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    fixed_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Indicator-based Condition (e.g., RSI > 70)
    indicator_type = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True
    )
    indicator_params = models.JSONField(null=True, blank=True)
    operator = models.CharField(
        max_length=20,
        choices=ComparisonOperator.choices,
        default=ComparisonOperator.GREATER,
        null=True, blank=True
    )
    threshold_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Value to compare indicator against"
    )
    threshold_value2 = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Second value for BETWEEN comparisons"
    )
    
    # Compare to another indicator (for crossovers)
    compare_to_indicator = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True,
        help_text="Compare to another indicator (for crossovers)"
    )
    compare_to_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Parameters for comparison indicator"
    )
    
    # Timeframe override
    timeframe_override = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        null=True,
        blank=True,
        help_text="Use different timeframe for this rule"
    )

    # Candle-based
    candle_part = models.CharField(
        max_length=10,
        choices=CandlePart.choices,
        null=True,
        blank=True,
        help_text="Part of candle to use (Low, High, etc.)"
    )
    candle_offset = models.PositiveIntegerField(
        default=0,
        help_text="0=Current Candle, 1=Previous Candle"
    )
    candle_lookback = models.PositiveIntegerField(
        default=1,
        help_text="Number of candles to look back"
    )
    
    # Trailing stops
    # Note: 'trailing_type' removed as 'sl_type' enum covers the logic (FIXED/PERCENTAGE/INDICATOR)
    
    trailing_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing value (points or percentage based on type)"
    )
    # trailing_indicator and params are covered by indicator_type/indicator_params when sl_type is TRAILING_INDICATOR
    
    # Time-based
    time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Exit after X minutes in loss"
    )
    
    # Emergency stop
    emergency_loss_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Emergency exit if loss exceeds this %"
    )
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.rule_group.strategy.name if self.rule_group else 'N/A'} - {self.sl_type}"


class TargetRule(BaseTimestampModel):
    """
    Target/profit booking configuration for a strategy.
    Supports multiple target types: fixed, R:R, trailing, time-based, etc.
    """
    rule_group = models.ForeignKey(
        RuleGroup,
        on_delete=models.CASCADE,
        related_name='target_rules',
        null=True, blank=True
    )
    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
        default=TargetType.FIXED_PERCENTAGE
    )
    
    # Fixed targets
    fixed_points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    fixed_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Risk-reward
    risk_reward_ratio = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Target = SL * ratio (e.g., 2.0 for 1:2)"
    )
    
    # Indicator-based exit
    indicator_type = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True
    )
    indicator_params = models.JSONField(null=True, blank=True)
    operator = models.CharField(
        max_length=20,
        choices=ComparisonOperator.choices,
        default=ComparisonOperator.GREATER,
        null=True, blank=True
    )
    threshold_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Value to compare indicator against"
    )
    threshold_value2 = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Second value for BETWEEN comparisons"
    )
    
    # Compare to another indicator (for crossovers)
    compare_to_indicator = models.CharField(
        max_length=30,
        choices=IndicatorType.choices,
        null=True,
        blank=True,
        help_text="Compare to another indicator (for crossovers)"
    )
    compare_to_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Parameters for comparison indicator"
    )
    
    # Timeframe override
    timeframe_override = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        null=True,
        blank=True,
        help_text="Use different timeframe for this rule"
    )
    
    # Trailing target
    trailing_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Time-based exits
    time_exit_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Exit after X minutes regardless of P&L"
    )
    eod_squareoff_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Square off time for intraday"
    )
    
    # Expiry exit (for options)
    expiry_exit_minutes_before = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Exit X minutes before expiry"
    )
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.rule_group.strategy.name if self.rule_group else 'N/A'} - {self.target_type}"
