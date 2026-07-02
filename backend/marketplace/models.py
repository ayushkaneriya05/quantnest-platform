from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class MarketplaceListing(BaseTimestampModel):
    STATUSES = [("PENDING", "Pending"), ("ACTIVE", "Active"), ("SUSPENDED", "Suspended")]
    SUBSCRIPTION_TYPES = [("ONE_TIME", "One Time"), ("MONTHLY", "Monthly"), ("YEARLY", "Yearly")]

    strategy = models.OneToOneField("strategies.Strategy", on_delete=models.CASCADE, related_name="marketplace_listing")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_listings")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES, default="MONTHLY")
    min_capital_required = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    expected_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    backtest_sharpe = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    live_sharpe = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    subscribers_count = models.PositiveIntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    listed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "marketplace_listing"
        ordering = ["-listed_at"]


class Subscription(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_subscriptions")
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name="subscriptions")
    subscription_type = models.CharField(max_length=20, choices=MarketplaceListing.SUBSCRIPTION_TYPES, default="MONTHLY")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="INR")
    payment_id = models.CharField(max_length=120, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_subscription"
        unique_together = ["user", "listing"]
        ordering = ["-subscribed_at"]


class StrategyReview(BaseTimestampModel):
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_reviews")
    rating = models.PositiveIntegerField(default=5)
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)
    use_duration_days = models.PositiveIntegerField(default=0)
    would_recommend = models.BooleanField(default=True)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "strategy_review"
        unique_together = ["listing", "user"]
        ordering = ["-created_at"]


class CreatorEarning(BaseTimestampModel):
    STATUSES = [("PENDING", "Pending"), ("PAID", "Paid")]

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="creator_earnings")
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name="earnings")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="earning_records")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "creator_earning"
        ordering = ["-created_at"]

