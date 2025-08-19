from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Instrument(models.Model):
    """
    Stores the master list of all tradable instruments (Nifty 100).
    """
    symbol = models.CharField(max_length=50, unique=True, db_index=True)
    company_name = models.CharField(max_length=255)

    def __str__(self):
        return self.symbol

class Watchlist(models.Model):
    """
    Links a user to a collection of instruments they are watching.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    instruments = models.ManyToManyField(Instrument, related_name='watchlists')

    def __str__(self):
        return f"{self.user.username}'s Watchlist"
    
class Account(models.Model):
    """
    Represents a user's paper trading account.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=1000000.00) # Start with 10 Lakhs
    margin = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Account"

class Position(models.Model):
    """
    Represents a user's holding in a specific instrument.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='positions')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('account', 'instrument')

    def __str__(self):
        return f"{self.account.user.username}'s Position in {self.instrument.symbol}"

class Order(models.Model):
    """
    Represents a single trading order placed by a user.
    """
    ORDER_TYPES = [
        ('MARKET', 'Market'),
        ('LIMIT', 'Limit'),
        ('STOP', 'Stop-Loss'),
        ('STOP_LIMIT', 'Stop-Limit')
    ]
    ORDER_STATUS = [
        ('OPEN', 'Open'),
        ('EXECUTED', 'Executed'),
        ('CANCELLED', 'Cancelled'),
    ]
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orders')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, default='OPEN')
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # For LIMIT and STOP_LIMIT
    trigger_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # For STOP and STOP_LIMIT
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

class TradeHistory(models.Model):
    """
    Logs every single executed trade for historical analysis.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    executed_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trade for Order {self.order.id} at {self.executed_price}"

