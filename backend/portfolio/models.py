"""
Portfolio Models

Manages user portfolios, capital allocation, fund transactions,
and exposure tracking.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import CapitalAllocationType, TransactionType, RebalanceFrequency


class Portfolio(BaseTimestampModel):
    """
    User's trading portfolio with capital and performance tracking.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portfolio'
    )
    
    name = models.CharField(max_length=100, default='Primary Portfolio')
    
    # Capital
    initial_capital = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Starting capital"
    )
    current_capital = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Current available capital"
    )
    invested_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Value currently in positions"
    )
    
    # Performance
    realized_pnl = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Total realized profit/loss"
    )
    unrealized_pnl = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Current unrealized P&L"
    )
    
    # High watermark for drawdown
    peak_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Highest portfolio value achieved"
    )
    peak_date = models.DateField(null=True, blank=True)
    
    # Daily tracking
    today_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    today_trades = models.PositiveIntegerField(default=0)
    
    # Broker-linked capital (if connected)
    broker_synced = models.BooleanField(default=False)
    last_broker_sync = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'portfolio'
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def total_value(self):
        return self.current_capital + self.invested_value + self.unrealized_pnl

    @property
    def current_drawdown(self):
        if self.peak_value <= 0:
            return 0
        return ((self.peak_value - self.total_value) / self.peak_value) * 100


class CapitalAllocation(BaseTimestampModel):
    """
    Capital allocated to a specific strategy.
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    strategy = models.OneToOneField(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='capital_allocation'
    )
    
    # Allocation method
    allocation_type = models.CharField(
        max_length=20,
        choices=CapitalAllocationType.choices,
        default=CapitalAllocationType.FIXED
    )
    
    # Allocation values
    allocated_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Fixed amount allocated"
    )
    allocated_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage of portfolio allocated"
    )
    
    # Current state
    utilized_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Amount currently in positions"
    )
    
    # Performance tracking
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    today_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Auto-rebalancing
    auto_rebalance = models.BooleanField(default=False)
    rebalance_frequency = models.CharField(
        max_length=20,
        choices=RebalanceFrequency.choices,
        default=RebalanceFrequency.WEEKLY
    )
    last_rebalance = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'portfolio_allocation'
        verbose_name = 'Capital Allocation'
        verbose_name_plural = 'Capital Allocations'

    def __str__(self):
        return f"{self.strategy.name}: ₹{self.allocated_amount}"

    @property
    def available_amount(self):
        """Computed: allocated minus utilized."""
        if self.allocation_type == 'PERCENTAGE' and self.portfolio:
            effective = (self.allocated_percentage / 100) * self.portfolio.current_capital
        else:
            effective = self.allocated_amount
        return max(effective - self.utilized_amount, 0)


class FundTransaction(BaseTimestampModel):
    """
    Record of fund deposits, withdrawals, and transfers.
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Reference
    notes = models.TextField(blank=True)
    
    # Approval (for large withdrawals)
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_transactions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'portfolio_transaction'
        verbose_name = 'Fund Transaction'
        verbose_name_plural = 'Fund Transactions'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.transaction_type}: {sign}{self.amount}"


class ExposureSnapshot(BaseTimestampModel):
    """
    Point-in-time snapshot of portfolio exposure.
    Used for historical tracking and reporting.
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='exposure_snapshots'
    )
    
    snapshot_time = models.DateTimeField()
    
    # Overall exposure
    total_exposure = models.DecimalField(max_digits=15, decimal_places=2)
    exposure_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Long/Short breakdown
    long_exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    short_exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Asset type breakdown (JSON)
    exposure_by_asset_type = models.JSONField(
        default=dict, blank=True,
        help_text="Exposure breakdown by equity/futures/options"
    )
    
    # Sector breakdown (JSON)
    exposure_by_sector = models.JSONField(
        default=dict, blank=True,
        help_text="Exposure breakdown by sector"
    )
    
    # Strategy breakdown (JSON)
    exposure_by_strategy = models.JSONField(
        default=dict, blank=True,
        help_text="Exposure breakdown by strategy"
    )
    
    # Position count
    open_positions_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'portfolio_exposure_snapshot'
        verbose_name = 'Exposure Snapshot'
        verbose_name_plural = 'Exposure Snapshots'
        ordering = ['-snapshot_time']

    def __str__(self):
        return f"Exposure at {self.snapshot_time.strftime('%Y-%m-%d %H:%M')}"


class DailyPerformance(BaseTimestampModel):
    """
    Daily performance record for the portfolio.
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='daily_performance'
    )
    
    date = models.DateField()
    
    # Capital
    opening_capital = models.DecimalField(max_digits=15, decimal_places=2)
    closing_capital = models.DecimalField(max_digits=15, decimal_places=2)
    
    # P&L
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    pnl_percentage = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    # Activity
    trades_count = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    
    # Exposure
    max_exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Fees
    brokerage_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxes_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'portfolio_daily_performance'
        verbose_name = 'Daily Performance'
        verbose_name_plural = 'Daily Performance Records'
        unique_together = ['portfolio', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.portfolio.name} - {self.date}"

    @property
    def win_rate(self):
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0
        return (self.winning_trades / total) * 100
