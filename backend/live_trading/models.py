from django.conf import settings
from django.db import models
from decimal import Decimal
from common.enums import CapitalAllocationType
from common.enums import OrderStatus, OrderType, ProductType, Side
from common.models import BaseTimestampModel


class TradingSession(BaseTimestampModel):
    SESSION_STATUSES = [
        ("RUNNING", "Running"),
        ("PAUSED", "Paused"),
        ("STOPPED", "Stopped"),
        ("STOPPING", "Stopping"),
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
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "live_trading_session"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} [{self.status}]"

    @property
    def trades_count(self):
        return self.allocation.trades.count() if self.allocation else 0

    @property
    def pnl(self):
        return self.allocation.total_pnl if self.allocation else Decimal("0")


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
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.CASCADE, related_name="strategy_allocations")
    allocation_type = models.CharField(max_length=20, choices=CapitalAllocationType.choices, default=CapitalAllocationType.FIXED)
    allocated_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    allocated_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    broker_equity_reference = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_over_allocated = models.BooleanField(default=False)
    breach_reason = models.TextField(blank=True)

    class Meta:
        db_table = "live_strategy_allocation"
        unique_together = ["user", "strategy", "broker_credential"]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} allocation on {self.broker_credential}"

    @property
    def invested_value(self):
        """Total capital invested in open positions."""
        from django.db.models import Sum
        result = self.positions.filter(quantity__gt=0).aggregate(
            total=Sum(models.F('quantity') * models.F('avg_price'))
        )['total']
        return result or Decimal("0")

    @property
    def unrealized_pnl(self):
        """Total unrealized P&L from open positions."""
        from django.db.models import Sum
        result = self.positions.filter(quantity__gt=0).aggregate(
            total=Sum('unrealized_pnl')
        )['total']
        return result or Decimal("0")

    @property
    def realized_pnl(self):
        """Total realized P&L from closed trades."""
        from django.db.models import Sum
        result = self.trades.aggregate(
            total=Sum('realized_pnl')
        )['total']
        return result or Decimal("0")

    @property
    def reserved_capital(self):
        """Capital reserved for pending orders."""
        from django.db.models import Sum
        result = LiveOrder.objects.filter(
            allocation=self,
            status__in=[OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL]
        ).aggregate(
            total=Sum(models.F('pending_quantity') * models.F('price'))
        )['total']
        return result or Decimal("0")

    @property
    def available_capital(self):
        """Available capital for new orders."""
        return max(
            Decimal("0"),
            self.allocated_capital - self.invested_value - self.reserved_capital
        )

    @property
    def total_pnl(self):
        """Total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl


class LiveOrder(BaseTimestampModel):
    STATUS_CHOICES = list(OrderStatus.choices) + [("UNKNOWN", "Unknown")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_orders")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_orders")
    session = models.ForeignKey(TradingSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    allocation = models.ForeignKey("live_trading.LiveStrategyAllocation", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_orders")
    broker_order_id = models.CharField(max_length=128, blank=True)
    exchange_order_id = models.CharField(max_length=128, blank=True)
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_orders")
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.MARKET)
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    filled_quantity = models.PositiveIntegerField(default=0)
    pending_quantity = models.PositiveIntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OrderStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "live_order"
        ordering = ["-placed_at"]


class LivePosition(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_positions")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_positions")
    allocation = models.ForeignKey("live_trading.LiveStrategyAllocation", on_delete=models.SET_NULL, null=True, blank=True, related_name="positions")
    broker_credential = models.ForeignKey("brokers.BrokerCredential", on_delete=models.CASCADE, related_name="live_positions", null=True, blank=True)
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_positions")
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    quantity = models.PositiveIntegerField()
    avg_price = models.DecimalField(max_digits=12, decimal_places=4)
    current_price = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    unrealized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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
    
    # Entry
    entry_price = models.DecimalField(max_digits=12, decimal_places=4)
    entry_time = models.DateTimeField()
    
    # Exit
    exit_price = models.DecimalField(max_digits=12, decimal_places=4)
    exit_time = models.DateTimeField()
  
    exit_reason = models.CharField(max_length=50, blank=True)
    
    # P&L (broker handles costs, but we track for analytics)
    gross_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Duration
    holding_duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "live_trade"
        ordering = ["-exit_time"]

    def __str__(self):
        result = 'WIN' if self.realized_pnl > 0 else 'LOSS'
        return f"{self.side} {self.instrument.symbol} - {result}"

    @property
    def is_winner(self):
        return self.realized_pnl > 0


class ExecutionLog(BaseTimestampModel):
    """Simplified execution log for broker order lifecycle tracking."""
    EVENT_TYPES = [
        ("CREATED", "Created"),
        ("PLACED", "Placed"),
        ("PARTIAL_FILL", "Partial Fill"),
        ("FILLED", "Filled"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("UNKNOWN", "Unknown"),
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
    """Track slippage for analytics - broker handles execution, we track for analysis."""
    order = models.OneToOneField(LiveOrder, on_delete=models.CASCADE, related_name="slippage_record")
    expected_price = models.DecimalField(max_digits=12, decimal_places=4)
    actual_price = models.DecimalField(max_digits=12, decimal_places=4)
    slippage_pct = models.DecimalField(max_digits=10, decimal_places=4)
    slippage_amount = models.DecimalField(max_digits=12, decimal_places=4)
    market_impact = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        db_table = "live_slippage_record"
