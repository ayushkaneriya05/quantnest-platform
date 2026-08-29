"""
Paper Trading Models

Simulates live trading with virtual money for strategy testing.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import (
    Side, OrderType, OrderStatus, ProductType,
    CapitalAllocationType, TransactionType, RebalanceFrequency
)
from decimal import Decimal


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
    # High watermark for drawdown
    peak_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Highest portfolio value achieved"
    )
    peak_date = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'portfolio'
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def total_value(self):
        # E = (C + sum_fixed + U) / (1 - sum_pct)
        fixed_allocs = self.allocations.filter(allocation_type='FIXED')
        pct_allocs = self.allocations.filter(allocation_type='PERCENTAGE')
        
        sum_fixed = sum((alloc.allocated_amount for alloc in fixed_allocs), Decimal("0"))
        sum_pct = sum((alloc.allocated_percentage for alloc in pct_allocs), Decimal("0")) / Decimal("100")
        
        numerator = self.current_capital + sum_fixed + self.unrealized_pnl
        denominator = Decimal("1") - sum_pct
        
        if denominator <= Decimal("0"):
            return Decimal("0") # Prevent division by zero or negative if over-allocated
            
        return numerator / denominator

    @property
    def invested_value(self):
        return sum(
            (position.invested_value
             for account in self.user.paper_accounts.all()
             for position in account.positions.all()),
            Decimal("0"),
        )

    @property
    def realized_pnl(self):
        return sum(
            (trade.net_pnl
             for account in self.user.paper_accounts.all()
             for trade in account.trades.all()),
            Decimal("0"),
        )

    @property
    def unrealized_pnl(self):
        return sum(
            (position.unrealized_pnl
             for account in self.user.paper_accounts.all()
             for position in account.positions.all()),
            Decimal("0"),
        )

    @property
    def today_pnl(self):
        from django.utils import timezone
        realized_today = sum(
            (trade.net_pnl
             for account in self.user.paper_accounts.all()
             for trade in account.trades.filter(exit_time__date=timezone.localdate())),
            Decimal("0"),
        )
        return realized_today + self.unrealized_pnl

    @property
    def today_trades(self):
        from django.utils import timezone
        return sum(
            account.trades.filter(exit_time__date=timezone.localdate()).count()
            for account in self.user.paper_accounts.all()
        )

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
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='capital_allocations'
    )
    deployed_version = models.ForeignKey(
        'strategies.StrategyVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paper_allocations',
        help_text='Pinned strategy version for this paper allocation'
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
    
    # Auto-rebalancing
    auto_rebalance = models.BooleanField(default=False)
    rebalance_frequency = models.CharField(
        max_length=20,
        choices=RebalanceFrequency.choices,
        default=RebalanceFrequency.WEEKLY
    )
    last_rebalance = models.DateTimeField(null=True, blank=True)
        
    class Meta:
        db_table = 'portfolio_allocation'
        verbose_name = 'Capital Allocation'
        verbose_name_plural = 'Capital Allocations'

    def __str__(self):
        return f"{self.strategy.name}: ₹{self.allocated_amount}"

    @property
    def effective_allocated(self):
        if self.allocation_type == CapitalAllocationType.PERCENTAGE and self.portfolio:
            portfolio_equity = self.portfolio.total_value
            return (self.allocated_percentage / Decimal("100")) * portfolio_equity
        return self.allocated_amount

    @property
    def available_amount(self):
        return max(self.effective_allocated - self.utilized_amount, Decimal("0"))

    @property
    def utilized_amount(self):
        account = getattr(self, "paper_account", None)
        return account.margin_used if account else Decimal("0")

    @property
    def total_pnl(self):
        account = getattr(self, "paper_account", None)
        return account.total_pnl if account else Decimal("0")

    @property
    def today_pnl(self):
        account = getattr(self, "paper_account", None)
        return account.today_pnl if account else Decimal("0")


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
    
    class Meta:
        db_table = 'portfolio_transaction'
        verbose_name = 'Fund Transaction'
        verbose_name_plural = 'Fund Transactions'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.transaction_type}: {sign}{self.amount}"


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
    
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    pnl_percentage = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    # Activity
    trades_count = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    
    # Costs
    brokerage_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    taxes_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    
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


class PaperAccount(BaseTimestampModel):
    """
    Virtual trading account for paper trading.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paper_accounts'
    )
    
    allocation = models.OneToOneField(
        'CapitalAllocation',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='paper_account',
        help_text="Capital allocation this paper account was created from"
    )
    
    name = models.CharField(max_length=100, default='Paper Account')
    
    # Capital
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    
    class Meta:
        db_table = 'paper_account'
        verbose_name = 'Paper Account'
        verbose_name_plural = 'Paper Accounts'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def reset(self):
        """Reset account to initial state."""
        self.current_balance = self.initial_balance
        self.save()

    @property
    def realized_pnl(self):
        return self.trades.aggregate(value=models.Sum("net_pnl"))["value"] or Decimal("0")

    @property
    def unrealized_pnl(self):
        return self.positions.aggregate(value=models.Sum("unrealized_pnl"))["value"] or Decimal("0")

    @property
    def total_pnl(self):
        return self.realized_pnl + self.unrealized_pnl

    @property
    def today_pnl(self):
        from django.utils import timezone
        realized_today = self.trades.filter(
            exit_time__date=timezone.localdate()
        ).aggregate(value=models.Sum("net_pnl"))["value"] or Decimal("0")
        return realized_today + self.unrealized_pnl

    @property
    def today_trades(self):
        from django.utils import timezone
        return self.trades.filter(exit_time__date=timezone.localdate()).count()

    @property
    def margin_used(self):
        return self.positions.aggregate(value=models.Sum("margin_blocked"))["value"] or Decimal("0")

    @property
    def margin_available(self):
        return max(Decimal("0"), self.current_balance - self.margin_used)


class PaperPosition(BaseTimestampModel):
    """
    Open position in a paper trading account.
    """
    account = models.ForeignKey(
        PaperAccount,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='paper_positions'
    )
    instrument = models.ForeignKey(
        'instruments.Instrument',
        on_delete=models.CASCADE,
        related_name='paper_positions'
    )
    
    # Position details
    side = models.CharField(max_length=10, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    avg_price = models.DecimalField(max_digits=12, decimal_places=4)
    
    # Current values
    current_price = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    unrealized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Realized (from partial closes)
    realized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Margin
    margin_blocked = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'paper_position'
        verbose_name = 'Paper Position'
        verbose_name_plural = 'Paper Positions'
        unique_together = ['account', 'instrument', 'side']

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument.symbol}"

    @property
    def current_value(self):
        return self.quantity * self.current_price

    @property
    def invested_value(self):
        return self.quantity * self.avg_price


class PaperOrder(BaseTimestampModel):
    """
    Order placed in paper trading.
    """
    account = models.ForeignKey(
        PaperAccount,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='paper_orders'
    )
    instrument = models.ForeignKey(
        'instruments.Instrument',
        on_delete=models.CASCADE,
        related_name='paper_orders'
    )
    
    # Order details
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.MARKET)
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    
    # Quantity & Price
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    trigger_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Execution
    filled_quantity = models.PositiveIntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    placed_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    # Reference
    order_tag = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'paper_order'
        verbose_name = 'Paper Order'
        verbose_name_plural = 'Paper Orders'
        ordering = ['-placed_at']

    def __str__(self):
        return f"{self.order_type} {self.side} {self.quantity} {self.instrument.symbol}"

    @property
    def is_filled(self):
        return self.status == OrderStatus.FILLED

    @property
    def is_pending(self):
        return self.status in [OrderStatus.PENDING, OrderStatus.PLACED]


class PaperTrade(BaseTimestampModel):
    """
    Completed trade (entry + exit) in paper trading.
    """
    account = models.ForeignKey(
        PaperAccount,
        on_delete=models.CASCADE,
        related_name='trades'
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='paper_trades'
    )
    instrument = models.ForeignKey(
        'instruments.Instrument',
        on_delete=models.CASCADE,
        related_name='paper_trades'
    )
    
    # Trade details
    side = models.CharField(max_length=10, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    
    # Entry
    entry_price = models.DecimalField(max_digits=12, decimal_places=4)
    entry_time = models.DateTimeField()
    entry_order = models.ForeignKey(
        PaperOrder,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entry_trades'
    )
    
    # Exit
    exit_price = models.DecimalField(max_digits=12, decimal_places=4)
    exit_time = models.DateTimeField()
    exit_order = models.ForeignKey(
        PaperOrder,
        on_delete=models.SET_NULL,
        null=True,
        related_name='exit_trades'
    )
    exit_reason = models.CharField(max_length=50, blank=True)
    
    # P&L
    gross_pnl = models.DecimalField(max_digits=12, decimal_places=2)
    net_pnl = models.DecimalField(max_digits=12, decimal_places=2)
    pnl_pct = models.DecimalField(max_digits=8, decimal_places=4)
    brokerage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    charges_json = models.JSONField(default=dict, blank=True)
    
    # Duration
    holding_duration_seconds = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'paper_trade'
        verbose_name = 'Paper Trade'
        verbose_name_plural = 'Paper Trades'
        ordering = ['-exit_time']

    def __str__(self):
        result = 'WIN' if self.net_pnl > 0 else 'LOSS'
        return f"{self.side} {self.instrument.symbol} - {result}"

    @property
    def is_winner(self):
        return self.net_pnl > 0


class PaperTradingSession(BaseTimestampModel):
    """
    Execution controller for paper trading. Mirrors TradingSession from live trading.
    Controls whether a paper deployment is RUNNING, PAUSED, or STOPPED.
    """
    SESSION_STATUSES = [
        ("RUNNING", "Running"),
        ("PAUSED", "Paused"),
        ("STOPPED", "Stopped"),
        ("ERROR", "Error"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paper_sessions"
    )
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='paper_sessions'
    )
    allocation = models.ForeignKey(
        'CapitalAllocation',
        on_delete=models.CASCADE,
        related_name='paper_sessions'
    )
    account = models.ForeignKey(
        'PaperAccount',
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUSES,
        default="PAUSED"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    @property
    def trades_count(self):
        return self.account.trades.count()

    @property
    def pnl(self):
        return self.account.total_pnl

    class Meta:
        db_table = "paper_trading_session"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} [Paper: {self.status}]"
