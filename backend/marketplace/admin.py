from django.contrib import admin

from .models import CreatorEarning, MarketplaceListing, StrategyReview, Subscription


@admin.register(MarketplaceListing)
class MarketplaceListingAdmin(admin.ModelAdmin):
    list_display = ["id", "strategy", "creator", "title", "price", "status", "avg_rating", "subscribers_count"]
    list_filter = ["status", "is_free", "is_featured", "is_verified"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "listing", "amount_paid", "is_active", "expires_at"]
    list_filter = ["is_active", "subscription_type"]


@admin.register(StrategyReview)
class StrategyReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "listing", "user", "rating", "is_verified_purchase", "created_at"]
    list_filter = ["rating", "is_verified_purchase"]


@admin.register(CreatorEarning)
class CreatorEarningAdmin(admin.ModelAdmin):
    list_display = ["id", "creator", "listing", "gross_amount", "net_amount", "status", "paid_at"]
    list_filter = ["status"]
