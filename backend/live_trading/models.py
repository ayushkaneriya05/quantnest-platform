from django.conf import settings
from django.db import models

from common.enums import CapitalAllocationType
from common.enums import OrderStatus, OrderType, ProductType, Side
from common.models import BaseTimestampModel


class TradingSession(BaseTimestampModel):
    SESSION_STATUSES = [
        ("RUNNING", "Running"),
        ("PAUSED", "Paused"),
        ("STOPPED", "Stopped"),
        ("ERROR", "Error"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_sessions")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="live_sessions")
    allocation = models.OneToOneField(
        "live_trading.LiveStrategyAllocation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="session",
    )
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_sessions")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUSES, default="PAUSED")
    trades_count = models.PositiveIntegerField(default=0)
    pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "live_trading_session"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} [{self.status}]"


class LivePortfolio(BaseTimestampModel):
    """
    User's live trading portfolio tracking real equity and drawdowns.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='live_portfolio'
    )
    
    name = models.CharField(max_length=100, default='Live Portfolio')
    
    # Capital
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    invested_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Performance
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # High watermark for drawdown
    peak_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    peak_date = models.DateField(null=True, blank=True)
    
    # Daily tracking
    today_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    today_trades = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'live_portfolio'
        verbose_name = 'Live Portfolio'
        verbose_name_plural = 'Live Portfolios'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def total_value(self):
        return self.current_capital + self.unrealized_pnl

    @property
    def current_drawdown(self):
        if self.peak_value <= 0:
            return 0
        return ((self.peak_value - self.total_value) / self.peak_value) * 100


class LiveStrategyAllocation(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_strategy_allocations")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="live_allocations")
    deployed_version = models.ForeignKey(
        'strategies.StrategyVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_allocations',
        help_text='Pinned strategy version for this live allocation'
    )
    portfolio = models.ForeignKey(LivePortfolio, on_delete=models.CASCADE, related_name="live_allocations")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.CASCADE, related_name="strategy_allocations")
    allocation_type = models.CharField(max_length=20, choices=CapitalAllocationType.choices, default=CapitalAllocationType.FIXED)
    allocated_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    allocated_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reserved_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    broker_equity_reference = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_over_allocated = models.BooleanField(default=False)
    breach_reason = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "live_strategy_allocation"
        unique_together = ["user", "strategy", "broker_credential"]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} allocation on {self.broker_credential}"


class LiveOrder(BaseTimestampModel):
    VALIDITIES = [("DAY", "Day"), ("IOC", "Immediate or Cancel"), ("GTC", "Good Till Cancelled")]
    SOURCE_TYPES = [
        ("STRATEGY", "Strategy"),
        ("EXTERNAL", "External / Manual"),
        ("RECOVERED", "Recovered"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_orders")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_orders")
    session = models.ForeignKey(TradingSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    allocation = models.ForeignKey("live_trading.LiveStrategyAllocation", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    portfolio = models.ForeignKey(LivePortfolio, on_delete=models.SET_NULL, null=True, blank=True, related_name="live_orders")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_orders")
    broker_order_id = models.CharField(max_length=128, blank=True)
    exchange_order_id = models.CharField(max_length=128, blank=True)
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_orders")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default="STRATEGY")
    reduce_only = models.BooleanField(default=False)
    requested_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.MARKET)
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    trigger_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    filled_quantity = models.PositiveIntegerField(default=0)
    pending_quantity = models.PositiveIntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    rejection_code = models.CharField(max_length=32, blank=True)
    validity = models.CharField(max_length=10, choices=VALIDITIES, default="DAY")
    placed_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "live_order"
        ordering = ["-placed_at"]


class LivePosition(BaseTimestampModel):
    SOURCE_TYPES = [
        ("STRATEGY", "Strategy"),
        ("EXTERNAL", "External / Manual"),
        ("RECOVERED", "Recovered"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_positions")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_positions")
    allocation = models.ForeignKey("live_trading.LiveStrategyAllocation", on_delete=models.SET_NULL, null=True, blank=True, related_name="positions")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.CASCADE, related_name="live_positions", null=True, blank=True)
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_positions")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default="STRATEGY")
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    avg_price = models.DecimalField(max_digits=12, decimal_places=4)
    current_price = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    unrealized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_broker_sync = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "live_position"
        unique_together = ["user", "strategy", "broker_credential", "instrument", "side"]


class LiveTrade(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_trades")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_trades")
    allocation = models.ForeignKey("live_trading.LiveStrategyAllocation", on_delete=models.SET_NULL, null=True, blank=True, related_name="trades")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_trades")
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_trades")
    exit_order = models.ForeignKey(LiveOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="closed_trades")
    side = models.CharField(max_length=10, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    entry_price = models.DecimalField(max_digits=12, decimal_places=4)
    entry_time = models.DateTimeField()
    exit_price = models.DecimalField(max_digits=12, decimal_places=4)
    exit_time = models.DateTimeField()
    realized_pnl = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "live_trade"
        ordering = ["-exit_time"]


class ExecutionLog(BaseTimestampModel):
    EVENT_TYPES = [
        ("PLACED", "Placed"),
        ("ACKNOWLEDGED", "Acknowledged"),
        ("PARTIAL_FILL", "Partial Fill"),
        ("FILLED", "Filled"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("MODIFIED", "Modified"),
        ("EXPIRED", "Expired"),
        ("PAUSED", "Paused"),
        ("STOPPED", "Stopped"),
    ]

    order = models.ForeignKey(LiveOrder, on_delete=models.CASCADE, related_name="execution_logs")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    message = models.TextField(blank=True)
    fill_quantity = models.PositiveIntegerField(default=0)
    fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "live_execution_log"
        ordering = ["-created_at"]


class SlippageRecord(BaseTimestampModel):
    order = models.OneToOneField(LiveOrder, on_delete=models.CASCADE, related_name="slippage_record")
    expected_price = models.DecimalField(max_digits=12, decimal_places=4)
    actual_price = models.DecimalField(max_digits=12, decimal_places=4)
    slippage_pct = models.DecimalField(max_digits=10, decimal_places=4)
    slippage_amount = models.DecimalField(max_digits=12, decimal_places=4)
    market_impact = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        db_table = "live_slippage_record"
