from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from common.enums import Side, TerminalOrderType, TerminalOrderStatus, PositionSide, TerminalExitReason

class Watchlist(models.Model):
    """
    Links a user to a collection of instruments they are watching.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='terminal_watchlists')
    name = models.CharField(max_length=60, default='Main')
    instruments = models.ManyToManyField("instruments.Instrument", related_name='trading_watchlists', blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.name}"

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'name'], name='terminal_watchlist_name')]


class Account(models.Model):
    """
    Represents a user's paper trading account, including balance and P&L.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=1000000.00)
    margin = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    charge_profile = models.ForeignKey('brokers.BrokerChargeProfile', null=True, blank=True, on_delete=models.SET_NULL)
    futures_margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    short_option_margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    charges_paid = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    starting_balance = models.DecimalField(max_digits=20, decimal_places=2, default=1000000)

    def __str__(self):
        return f"{self.user.username}'s Account"

class Position(models.Model):
    """
    Represents a user's holding in a specific instrument, including risk management.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='positions')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=20, decimal_places=8)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('account', 'instrument')

    def __str__(self):
        return f"{self.account.user.username}'s Position in {self.instrument.name}"

class Order(models.Model):
    request_id = models.UUIDField(null=True, unique=True, editable=False)
    """
    Represents a single trading order placed by a user with a clear lifecycle.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orders')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=TerminalOrderType.choices)
    status = models.CharField(max_length=10, choices=TerminalOrderStatus.choices, default=TerminalOrderStatus.OPEN, db_index=True)
    transaction_type = models.CharField(max_length=4, choices=Side.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reserved_cash = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    trigger_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    filled_quantity = models.PositiveIntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    reduce_only = models.BooleanField(default=False)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    charge_profile_snapshot = models.JSONField(default=dict)
    
    # OCO (One Cancels Other) & Position Linking fields
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    eligible_at = models.DateTimeField(default=timezone.now)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['account', 'status'], name='terminal_account_status_idx')]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.instrument.name} @ {self.price or 'Market'}"

class TradeHistory(models.Model):
    """
    Logs every single executed trade for historical analysis and P&L calculation.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    executed_price = models.DecimalField(max_digits=20, decimal_places=8)
    quantity = models.PositiveIntegerField()
    charges = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    charges_breakdown = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Trade for Order {self.order.id} at {self.executed_price}"

class ClosedPositionLog(models.Model):
    """
    Logs round-trip trades (Closed Positions) for Realized P&L reporting.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='closed_positions')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    side = models.CharField(max_length=5, choices=PositionSide.choices)
    quantity = models.PositiveIntegerField()
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    exit_price = models.DecimalField(max_digits=20, decimal_places=8)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    gross_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    recorded_charges = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    exit_reason = models.CharField(max_length=100, choices=TerminalExitReason.choices, default=TerminalExitReason.MANUAL)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['account', '-exit_time'], name='terminal_close_time_idx')]

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument.name} - P&L: {self.realized_pnl}"
