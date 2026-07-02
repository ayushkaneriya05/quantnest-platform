from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from analytics.models import PerformanceSnapshot
from backtesting.models import BacktestMetrics
from common.enums import StrategyVisibility

from .models import CreatorEarning, MarketplaceListing, StrategyReview, Subscription


class MarketplaceService:
    PLATFORM_FEE_RATE = Decimal("0.20")

    @staticmethod
    def publish_listing(user, strategy, payload):
        metrics = (
            BacktestMetrics.objects.filter(run__strategy=strategy, run__user=user)
            .order_by("-run__completed_at", "-run__created_at")
            .first()
        )
        latest_snapshot = (
            PerformanceSnapshot.objects.filter(strategy=strategy, user=user)
            .order_by("-date")
            .first()
        )

        defaults = {
            "creator": user,
            "title": payload.get("title") or strategy.name,
            "description": payload.get("description") or strategy.description or "",
            "price": Decimal(str(payload.get("price") or 0)),
            "is_free": bool(payload.get("is_free", False)),
            "subscription_type": payload.get("subscription_type", "MONTHLY"),
            "min_capital_required": Decimal(str(payload.get("min_capital_required") or 0)),
            "expected_drawdown": metrics.max_drawdown_pct if metrics else Decimal("0"),
            "backtest_sharpe": metrics.sharpe_ratio if metrics else Decimal("0"),
            "live_sharpe": latest_snapshot.sharpe_ratio_30d if latest_snapshot else Decimal("0"),
            "is_featured": bool(payload.get("is_featured", False)),
            "status": payload.get("status", "ACTIVE"),
            "is_verified": bool(metrics),
        }
        if defaults["is_free"]:
            defaults["price"] = Decimal("0")

        listing, _ = MarketplaceListing.objects.update_or_create(
            strategy=strategy,
            defaults=defaults,
        )

        if strategy.visibility != StrategyVisibility.MARKETPLACE:
            strategy.visibility = StrategyVisibility.MARKETPLACE
            strategy.save(update_fields=["visibility", "updated_at"])

        MarketplaceService.refresh_listing_rating(listing)
        MarketplaceService.refresh_listing_subscribers(listing)
        return listing

    @staticmethod
    def subscribe(user, listing, auto_renew=False):
        if listing.creator_id == user.id:
            raise ValueError("Creators cannot subscribe to their own listing")
        if listing.status != "ACTIVE":
            raise ValueError("Only active listings can be subscribed to")

        amount = Decimal("0") if listing.is_free else Decimal(str(listing.price or 0))
        if listing.subscription_type == "ONE_TIME":
            expires_at = None
        elif listing.subscription_type == "YEARLY":
            expires_at = timezone.now() + timedelta(days=365)
        else:
            expires_at = timezone.now() + timedelta(days=30)

        subscription, _ = Subscription.objects.update_or_create(
            user=user,
            listing=listing,
            defaults={
                "subscription_type": listing.subscription_type,
                "amount_paid": amount,
                "currency": "INR",
                "payment_id": f"SIM-{listing.id}-{user.id}",
                "expires_at": expires_at,
                "auto_renew": auto_renew,
                "is_active": True,
                "cancelled_at": None,
            },
        )

        fee = (amount * MarketplaceService.PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        CreatorEarning.objects.update_or_create(
            subscription=subscription,
            defaults={
                "creator": listing.creator,
                "listing": listing,
                "gross_amount": amount,
                "platform_fee": fee,
                "net_amount": amount - fee,
                "status": "PENDING",
            },
        )

        MarketplaceService.refresh_listing_subscribers(listing)
        return subscription

    @staticmethod
    def cancel_subscription(subscription):
        subscription.is_active = False
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=["is_active", "cancelled_at", "updated_at"])
        MarketplaceService.refresh_listing_subscribers(subscription.listing)
        return subscription

    @staticmethod
    def refresh_listing_subscribers(listing):
        listing.subscribers_count = listing.subscriptions.filter(is_active=True).count()
        listing.save(update_fields=["subscribers_count", "updated_at"])
        return listing

    @staticmethod
    def refresh_listing_rating(listing):
        stats = StrategyReview.objects.filter(listing=listing).aggregate(avg_rating=Avg("rating"))
        listing.avg_rating = Decimal(str(stats["avg_rating"] or 0)).quantize(Decimal("0.01"))
        listing.total_reviews = listing.reviews.count()
        listing.save(update_fields=["avg_rating", "total_reviews", "updated_at"])
        return listing

    @staticmethod
    def listing_detail_payload(listing, user=None):
        reviews = list(listing.reviews.select_related("user").order_by("-is_verified_purchase", "-created_at")[:8])
        latest_snapshot = (
            PerformanceSnapshot.objects.filter(strategy=listing.strategy, user=listing.creator)
            .order_by("-date")
            .first()
        )
        active_subscription = None
        my_review = None
        if user and user.is_authenticated:
            active_subscription = listing.subscriptions.filter(user=user, is_active=True).first()
            my_review = listing.reviews.filter(user=user).first()

        return {
            "listing": listing,
            "reviews": reviews,
            "latest_snapshot": latest_snapshot,
            "active_subscription": active_subscription,
            "my_review": my_review,
        }

    @staticmethod
    def creator_dashboard(user):
        listings = list(
            MarketplaceListing.objects.filter(creator=user)
            .select_related("strategy", "creator")
            .order_by("-listed_at")
        )
        earnings = CreatorEarning.objects.filter(creator=user)
        pending_amount = earnings.filter(status="PENDING").aggregate(total=Sum("net_amount"))["total"] or Decimal("0")
        paid_amount = earnings.filter(status="PAID").aggregate(total=Sum("net_amount"))["total"] or Decimal("0")
        totals = earnings.aggregate(total=Sum("net_amount"), gross=Sum("gross_amount"))
        listing_ids = [listing.id for listing in listings]
        top_reviews = list(
            StrategyReview.objects.filter(listing_id__in=listing_ids)
            .select_related("listing", "user")
            .order_by("-created_at")[:8]
        )
        return {
            "summary": {
                "listings": len(listings),
                "active_listings": sum(1 for listing in listings if listing.status == "ACTIVE"),
                "subscribers": sum(listing.subscribers_count for listing in listings),
                "avg_rating": round(
                    sum(float(listing.avg_rating or 0) for listing in listings) / len(listings), 2
                ) if listings else 0,
                "pending_amount": pending_amount,
                "paid_amount": paid_amount,
                "lifetime_net_amount": totals["total"] or Decimal("0"),
                "lifetime_gross_amount": totals["gross"] or Decimal("0"),
            },
            "listings": listings,
            "earnings": list(earnings.select_related("listing", "subscription", "subscription__user")[:20]),
            "reviews": top_reviews,
        }

    @staticmethod
    def subscription_summary(user):
        subscriptions = Subscription.objects.filter(user=user).select_related("listing", "listing__creator")
        return {
            "active": subscriptions.filter(is_active=True).count(),
            "inactive": subscriptions.filter(is_active=False).count(),
            "auto_renew": subscriptions.filter(is_active=True, auto_renew=True).count(),
            "monthly_spend": sum(float(sub.amount_paid or 0) for sub in subscriptions.filter(is_active=True)),
        }
