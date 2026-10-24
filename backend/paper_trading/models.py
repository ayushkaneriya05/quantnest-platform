"""
Paper Trading Models

Simulates live trading with virtual money for strategy testing.
"""
from django.db import models
from django.db.models.functions import Coalesce, Greatest
from django.conf import settings
from django.utils import timezone
from common.models import BaseTimestampModel
from common.enums import (
    Side, OrderType, OrderStatus, ProductType,
    TransactionType, ExecutionSessionStatus
)
from decimal import Decimal
import uuid


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
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'portfolio'
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def total_value(self):
        account_balance = self.user.paper_accounts.aggregate(total=models.Sum("current_balance"))["total"] or Decimal("0")
        return self.current_capital + account_balance + self.unrealized_pnl

    @property
    def allocated_capital(self):
        return self.allocations.aggregate(total=models.Sum("allocated_amount"))["total"] or Decimal("0")

    @property
    def invested_value(self):
        return PaperPosition.objects.filter(account__user_id=self.user_id).aggregate(
            total=models.Sum(models.F('quantity') * models.F('avg_price') * models.F('instrument__qty_multiplier'))
        )['total'] or Decimal('0')

    @property
    def realized_pnl(self):
        return PaperTrade.objects.filter(account__user_id=self.user_id).aggregate(
            total=models.Sum('net_pnl'))['total'] or Decimal('0')

    @property
    def unrealized_pnl(self):
        return PaperPosition.objects.filter(account__user_id=self.user_id).aggregate(
            total=models.Sum('unrealized_pnl'))['total'] or Decimal('0')

    @property
    def today_pnl(self):
        from django.utils import timezone
        realized_today = PaperTrade.objects.filter(account__user_id=self.user_id,
            exit_time__date=timezone.localdate()).aggregate(total=models.Sum('net_pnl'))['total'] or Decimal('0')
        return realized_today + self.unrealized_pnl

    @property
    def today_trades(self):
        from django.utils import timezone
        return PaperTrade.objects.filter(account__user_id=self.user_id, exit_time__date=timezone.localdate()).count()

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
    
    allocated_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Capital assigned to this deployment"
    )

    class Meta:
        db_table = 'portfolio_allocation'
        verbose_name = 'Capital Allocation'
        verbose_name_plural = 'Capital Allocations'
        constraints = [models.UniqueConstraint(fields=['strategy', 'deployed_version'], name='paper_strategy_version_unique')]

    def __str__(self):
        return f"{self.strategy.name}: ₹{self.allocated_amount}"

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


class PaperAccountQuerySet(models.QuerySet):
    def with_totals(self):
        """Read ledger totals once for lists; execution still reads fresh balances."""
        money = models.DecimalField(max_digits=18, decimal_places=4)
        zero = models.Value(Decimal("0"), output_field=money)
        positions = PaperPosition.objects.filter(account_id=models.OuterRef("pk")).order_by().values("account_id")
        return self.annotate(
            annotated_realized_pnl=Coalesce(models.Sum("trades__net_pnl"), zero),
            annotated_trade_count=models.Count("trades"),
            annotated_today_trades=models.Count("trades", filter=models.Q(
                trades__exit_time__date=timezone.localdate())),
            annotated_used_capital=Coalesce(models.Subquery(
                positions.annotate(total=models.Sum("margin_blocked")).values("total")[:1],
                output_field=money), zero),
            annotated_unrealized_pnl=Coalesce(models.Subquery(
                positions.annotate(total=models.Sum("unrealized_pnl")).values("total")[:1],
                output_field=money), zero),
            annotated_open_positions=Coalesce(models.Subquery(
                positions.annotate(total=models.Count("pk")).values("total")[:1]), models.Value(0)),
        ).annotate(
            annotated_available_capital=Greatest(zero, models.F("current_balance") - models.F("annotated_used_capital")),
        )


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
        on_delete=models.CASCADE,
        related_name='paper_account',
        help_text="Capital allocation this paper account was created from"
    )
    
    objects = PaperAccountQuerySet.as_manager()

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
        return self.quantity * self.current_price * self.instrument.qty_multiplier

    @property
    def invested_value(self):
        return self.quantity * self.avg_price * self.instrument.qty_multiplier


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
    reason = models.CharField(max_length=255, blank=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
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
    slippage_pct_applied = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    slippage_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
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
    exit_reason = models.TextField(blank=True)
    
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
        indexes = [models.Index(fields=['account', '-exit_time'], name='paper_close_time_idx')]

    def __str__(self):
        result = 'WIN' if self.net_pnl > 0 else 'LOSS'
        return f"{self.side} {self.instrument.symbol} - {result}"

    @property
    def is_winner(self):
        return self.net_pnl > 0


class PaperTradingSession(BaseTimestampModel):
    applied_version = models.ForeignKey('strategies.StrategyVersion', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    applied_at = models.DateTimeField(null=True, blank=True)
    """
    Execution controller for paper trading. Mirrors TradingSession from live trading.
    Controls whether a paper deployment is RUNNING, PAUSED, or STOPPED.
    """
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
    slippage_pct = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=0,
        help_text='Simulated adverse fill adjustment as a percentage.'
    )
    charge_profile = models.ForeignKey(
        'brokers.BrokerChargeProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paper_sessions',
    )
    charge_profile_snapshot = models.JSONField(default=dict, blank=True)
    include_charges = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=ExecutionSessionStatus.choices,
        default="PAUSED"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "paper_trading_session"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["account"], name="paper_session_account_unique"),
            models.UniqueConstraint(fields=["allocation"], name="paper_session_allocation_unique"),
        ]

    def __str__(self):
        return f"{self.strategy.name} [Paper: {self.status}]"
