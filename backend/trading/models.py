from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Watchlist(models.Model):
    """
    Links a user to a collection of instruments they are watching.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    instruments = models.ManyToManyField("instruments.Instrument", related_name='trading_watchlists', blank=True)

    def __str__(self):
        return f"{self.user.username}'s Watchlist"
    
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

    def __str__(self):
        return f"{self.user.username}'s Account"

class Position(models.Model):
    """
    Represents a user's holding in a specific instrument, including risk management.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='positions')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('account', 'instrument')

    def __str__(self):
        return f"{self.account.user.username}'s Position in {self.instrument.symbol}"

class Order(models.Model):
    """
    Represents a single trading order placed by a user with a clear lifecycle.
    """
    ORDER_TYPES = [
        ('MARKET', 'Market'),
        ('LIMIT', 'Limit'),
        ('STOP', 'Stop-Loss'),
        ('STOP_LIMIT', 'Stop-Limit')
    ]
    ORDER_STATUS = [
        ('OPEN', 'Open'),          # Order is active and waiting to be filled
        ('COMPLETE', 'Complete'),    # Order has been fully filled
        ('CANCELLED', 'Cancelled'),  # User cancelled the order
        ('REJECTED', 'Rejected'),    # The system rejected the order (e.g., insufficient funds)
    ]
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orders')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, default='OPEN', db_index=True)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    trigger_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # OCO (One Cancels Other) & Position Linking fields
    is_oco = models.BooleanField(default=False)
    oco_linked_order = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='linked_to')
    position_link = models.ForeignKey(Position, null=True, blank=True, on_delete=models.SET_NULL, related_name='exit_orders')
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.instrument.symbol} @ {self.price or 'Market'}"

class TradeHistory(models.Model):
    """
    Logs every single executed trade for historical analysis and P&L calculation.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    executed_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Trade for Order {self.order.id} at {self.executed_price}"

class ClosedPositionLog(models.Model):
    """
    Logs round-trip trades (Closed Positions) for Realized P&L reporting.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='closed_positions')
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    side = models.CharField(max_length=5) # 'LONG' or 'SHORT'
    quantity = models.PositiveIntegerField()
    entry_price = models.DecimalField(max_digits=10, decimal_places=2)
    exit_price = models.DecimalField(max_digits=10, decimal_places=2)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument.symbol} - P&L: {self.realized_pnl}"
