import uuid
from decimal import Decimal

from common.enums import (
    ExecutionSessionStatus,
    OrderIntent,
    OrderStatus,
    OrderType,
    ProductType,
    Side,
)
from common.models import BaseTimestampModel
from django.conf import settings
from django.db import models
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from execution.order_reports import ACTIVE


class TradingSession(BaseTimestampModel):
    applied_version = models.ForeignKey('strategies.StrategyVersion', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    applied_at = models.DateTimeField(null=True, blank=True)
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
    status = models.CharField(max_length=20, choices=ExecutionSessionStatus.choices, default="PAUSED")
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "live_trading_session"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.strategy.name} [{self.status}]"


class LiveStrategyAllocationQuerySet(models.QuerySet):
    def with_totals(self):
        """Shared financial snapshot for deployment and allocation responses."""
        decimal_field = DecimalField(max_digits=18, decimal_places=4)
        zero_money = Value(Decimal("0"), output_field=decimal_field)

        open_positions = LivePosition.objects.filter(allocation_id=OuterRef("pk"), quantity__gt=0)
        used_capital = open_positions.order_by().values("allocation_id").annotate(
            total=Sum(ExpressionWrapper(F("quantity") * F("avg_price") * F("instrument__qty_multiplier"), output_field=decimal_field))
        ).values("total")[:1]
        unrealized_pnl = open_positions.order_by().values("allocation_id").annotate(
            total=Sum("unrealized_pnl")
        ).values("total")[:1]
        realized_pnl = LiveTrade.objects.filter(allocation_id=OuterRef("pk")).order_by().values(
            "allocation_id"
        ).annotate(total=Sum("realized_pnl")).values("total")[:1]
        reserved_value = ExpressionWrapper(
            Greatest(F("pending_quantity"), F("quantity") - F("filled_quantity"))
            * Coalesce(F("price"), zero_money) * F('instrument__qty_multiplier'),
            output_field=decimal_field,
        )
        reserved_capital = LiveOrder.objects.filter(
            allocation_id=OuterRef("pk"), intent=OrderIntent.ENTRY, status__in=ACTIVE
        ).order_by().values("allocation_id").annotate(total=Sum(reserved_value)).values("total")[:1]
        allocation_trades = LiveTrade.objects.filter(allocation_id=OuterRef("pk")).order_by().values(
            "allocation_id"
        ).annotate(total=Count("id")).values("total")[:1]

        allocation_queryset = self.select_related(
            "strategy", "broker_credential", "deployed_version"
        ).annotate(
            annotated_used_capital=Coalesce(Subquery(used_capital, output_field=decimal_field), zero_money),
            annotated_reserved_capital=Coalesce(Subquery(reserved_capital, output_field=decimal_field), zero_money),
            annotated_realized_pnl=Coalesce(Subquery(realized_pnl, output_field=decimal_field), zero_money),
            annotated_unrealized_pnl=Coalesce(Subquery(unrealized_pnl, output_field=decimal_field), zero_money),
            annotated_trade_count=Coalesce(Subquery(allocation_trades, output_field=IntegerField()), Value(0)),
        ).annotate(
            annotated_available_capital=Greatest(
                zero_money,
                F("allocated_capital") - F("annotated_used_capital") - F("annotated_reserved_capital") + F("annotated_realized_pnl"),
            ),
            annotated_total_pnl=F("annotated_realized_pnl") + F("annotated_unrealized_pnl"),
        )

        return allocation_queryset.annotate(
            annotated_open_positions=Coalesce(Subquery(
                open_positions.order_by().values("allocation_id").annotate(total=Count("id")).values("total")[:1]), Value(0)),
        )


class LiveStrategyAllocation(BaseTimestampModel):
    objects = LiveStrategyAllocationQuerySet.as_manager()

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
    allocated_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
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
            total=Sum(models.F('quantity') * models.F('avg_price') * models.F('instrument__qty_multiplier'))
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
            intent=OrderIntent.ENTRY,
            status__in=ACTIVE
        ).aggregate(
            total=Sum(
                Greatest(
                    models.F('pending_quantity'),
                    models.F('quantity') - models.F('filled_quantity'),
                ) * models.F('price') * models.F('instrument__qty_multiplier')
            )
        )['total']
        return result or Decimal("0")

    @property
    def available_capital(self):
        """Available capital for new orders."""
        return max(
            Decimal("0"),
            self.allocated_capital - self.invested_value - self.reserved_capital + self.realized_pnl
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
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    exchange_order_id = models.CharField(max_length=128, blank=True)
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE, related_name="live_orders")
    reason = models.CharField(max_length=255, blank=True)
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.MARKET)
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.INTRADAY)
    side = models.CharField(max_length=10, choices=Side.choices)
    price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    filled_quantity = models.PositiveIntegerField(default=0)
    pending_quantity = models.PositiveIntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    filled_value = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    strategy_version = models.ForeignKey("strategies.StrategyVersion", on_delete=models.PROTECT, null=True, related_name="live_orders")
    intent = models.CharField(max_length=10, choices=OrderIntent.choices, default=OrderIntent.ENTRY)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OrderStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    broker_ordered_at = models.DateTimeField(null=True, blank=True)
    broker_updated_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # New fields for broker reconciliation
    reconciliation_status = models.CharField(
        max_length=20,
        choices=[('MATCHED', 'Matched'), ('PENDING', 'Pending'), ('MISMATCH', 'Mismatch')],
        default='PENDING',
        help_text="Reconciliation status with broker WebSocket"
    )
    reconciliation_attempts = models.PositiveIntegerField(default=0, help_text="Number of reconciliation attempts")
    last_reconciliation = models.DateTimeField(null=True, blank=True, help_text="Last reconciliation timestamp")

    class Meta:
        db_table = "live_order"
        ordering = ["-placed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["broker_credential", "broker_order_id"],
                condition=models.Q(broker_credential__isnull=False) & ~models.Q(broker_order_id=""),
                name="uniq_live_order_broker_id_per_credential",
            ),
        ]


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
    opened_at = models.DateTimeField(default=timezone.now)
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
  
    exit_reason = models.TextField(blank=True)
    
    # P&L (broker handles costs, but we track for analytics)
    gross_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Duration
    holding_duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "live_trade"
        ordering = ["-exit_time"]
        indexes = [models.Index(fields=['user', '-exit_time'], name='live_close_time_idx')]

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
