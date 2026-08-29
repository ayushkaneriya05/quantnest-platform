"""
Rules Engine app - trading rules, signals, time filters, stop loss, and targets.
"""
from django.db import models
from common.models import BaseTimestampModel
from common.enums import (
    CandleTimeframe, MarketSession, LogicalOperator,
    RuleType, OperandType, ComparisonOperator, Timezone
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
    
    # Action (e.g., for Stop Loss and Target groups)
    action = models.CharField(
        max_length=50,
        choices=[
            ('EXIT_ALL', 'Exit Full Position'),
            ('PARTIAL_EXIT', 'Partial Exit'),
            ('MOVE_TO_BREAKEVEN', 'Move Stop Loss to Breakeven')
        ],
        null=True,
        blank=True,
    )
    action_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Params for action, e.g., {'exit_pct': 50}"
    )

    class Meta:
        ordering = ['rule_type', 'priority']

    def __str__(self):
        return f"{self.strategy.name} - {self.rule_type} Group ({self.logical_operator})"


class Rule(BaseTimestampModel):
    """
    Individual trading rule/condition using Universal Operand Architecture.
    Evaluates: [Operand A] [Comparison] [Operand B]
    """
    rule_group = models.ForeignKey(
        RuleGroup,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    
    # Operand A (Left Side)
    operand_a_type = models.CharField(
        max_length=50,
        choices=OperandType.choices,
        default=OperandType.LTP
    )
    operand_a_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Parameters for Operand A"
    )
    operand_a_timeframe = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        null=True,
        blank=True,
        help_text="Timeframe override for Operand A"
    )
    
    # Comparison
    comparison = models.CharField(
        max_length=20,
        choices=ComparisonOperator.choices,
        default=ComparisonOperator.GREATER
    )
    
    # Operand B (Right Side)
    operand_b_type = models.CharField(
        max_length=50,
        choices=OperandType.choices,
        default=OperandType.CONSTANT
    )
    operand_b_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Parameters for Operand B (e.g., {'value': 100})"
    )
    operand_b_timeframe = models.CharField(
        max_length=10,
        choices=CandleTimeframe.choices,
        null=True,
        blank=True,
        help_text="Timeframe override for Operand B"
    )
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.operand_a_type} {self.comparison} {self.operand_b_type}"
