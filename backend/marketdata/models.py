# backend/marketdata/models.py
from django.db import models
from django.utils import timezone

class MarketDataToken(models.Model):
    """
    Singleton-like model to store the Fyers market-data access token and refresh token.
    You can keep one row per token (we will use get_or_create(pk=1) in views).
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_type = models.CharField(max_length=32, default="Bearer", blank=True)
    expires_at = models.DateTimeField(null=True, blank=True,)  # UTC
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True) # Added active field

    class Meta:
        verbose_name = "Market Data Token"
        verbose_name_plural = "Market Data Tokens"

    def is_valid(self):
        if not self.access_token:
            return False
        if self.expires_at is None:
            return True
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"MarketDataToken(valid={self.is_valid()}, expires_at={self.expires_at})"
