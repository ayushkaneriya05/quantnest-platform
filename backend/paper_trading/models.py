"""
Paper Trading Models

Simulates live trading with virtual money for strategy testing.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import Side, OrderType, OrderStatus, ProductType


class PaperAccount(BaseTimestampModel):
    """
    Virtual trading account for paper trading.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paper_accounts'
    )
    
    name = models.CharField(max_length=100, default='Paper Account')
    
    # Capital
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    
    # P&L
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Daily tracking
    today_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    today_trades = models.PositiveIntegerField(default=0)
    
    # Margins
    margin_used = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    margin_available = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'paper_account'
        verbose_name = 'Paper Account'
        verbose_name_plural = 'Paper Accounts'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def reset(self):
        """Reset account to initial state."""
        self.current_balance = self.initial_balance
        self.total_pnl = 0
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.today_pnl = 0
        self.today_trades = 0
        self.margin_used = 0
        self.margin_available = self.initial_balance
        self.save()


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
    unrealized_pnl_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
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
    slippage_applied = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
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
    brokerage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    slippage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=12, decimal_places=2)
    pnl_pct = models.DecimalField(max_digits=8, decimal_places=4)
    
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
