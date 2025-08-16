# backend/ohlc/models.py
from django.db import models

class OHLC(models.Model):
    symbol = models.CharField(max_length=32)
    tf = models.CharField(max_length=8)  # '1m','5m',...
    ts = models.DateTimeField()           # candle start UTC
    open = models.DecimalField(max_digits=14, decimal_places=4)
    high = models.DecimalField(max_digits=14, decimal_places=4)
    low = models.DecimalField(max_digits=14, decimal_places=4)
    close = models.DecimalField(max_digits=14, decimal_places=4)
    volume = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ('symbol','tf','ts')
