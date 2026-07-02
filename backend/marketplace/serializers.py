from django.utils import timezone
from rest_framework import serializers

from .models import CreatorEarning, MarketplaceListing, StrategyReview, Subscription


class MarketplaceListingSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True)
    strategy_status = serializers.CharField(source="strategy.status", read_only=True)
    strategy_visibility = serializers.CharField(source="strategy.visibility", read_only=True)
    has_active_subscription = serializers.SerializerMethodField()
    my_subscription_id = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    my_review_id = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceListing
        fields = [
            "id",
            "strategy",
            "strategy_name",
            "strategy_status",
            "strategy_visibility",
            "creator",
            "creator_name",
            "title",
            "description",
            "price",
            "is_free",
            "subscription_type",
            "min_capital_required",
            "expected_drawdown",
            "backtest_sharpe",
            "live_sharpe",
            "subscribers_count",
            "avg_rating",
            "total_reviews",
            "is_featured",
            "is_verified",
            "status",
            "listed_at",
            "has_active_subscription",
            "my_subscription_id",
            "can_review",
            "my_review_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "creator",
            "subscribers_count",
            "avg_rating",
            "total_reviews",
            "is_verified",
            "listed_at",
            "has_active_subscription",
            "my_subscription_id",
            "can_review",
            "my_review_id",
            "created_at",
            "updated_at",
        ]

    def _request_user(self):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return request.user

    def get_has_active_subscription(self, obj):
        user = self._request_user()
        if not user:
            return False
        return obj.subscriptions.filter(user=user, is_active=True).exists()

    def get_my_subscription_id(self, obj):
        user = self._request_user()
        if not user:
            return None
        subscription = obj.subscriptions.filter(user=user).order_by("-subscribed_at").first()
        return subscription.id if subscription else None

    def get_can_review(self, obj):
        user = self._request_user()
        if not user:
            return False
        if obj.creator_id == user.id:
            return False
        return obj.subscriptions.filter(user=user, is_active=True).exists()

    def get_my_review_id(self, obj):
        user = self._request_user()
        if not user:
            return None
        review = obj.reviews.filter(user=user).first()
        return review.id if review else None


class SubscriptionSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_creator_name = serializers.CharField(source="listing.creator.username", read_only=True)
    listing_status = serializers.CharField(source="listing.status", read_only=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "listing",
            "listing_title",
            "listing_creator_name",
            "listing_status",
            "subscription_type",
            "amount_paid",
            "currency",
            "payment_id",
            "subscribed_at",
            "expires_at",
            "days_remaining",
            "auto_renew",
            "is_active",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "subscription_type",
            "amount_paid",
            "currency",
            "payment_id",
            "subscribed_at",
            "expires_at",
            "days_remaining",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]

    def get_days_remaining(self, obj):
        if not obj.expires_at:
            return None
        remaining = obj.expires_at - timezone.now()
        return max(remaining.days, 0)


class StrategyReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = StrategyReview
        fields = [
            "id",
            "listing",
            "username",
            "rating",
            "title",
            "comment",
            "use_duration_days",
            "would_recommend",
            "is_verified_purchase",
            "helpful_count",
            "is_owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "is_verified_purchase",
            "helpful_count",
            "is_owner",
            "created_at",
            "updated_at",
        ]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.user_id == request.user.id


class CreatorEarningSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    subscription_user = serializers.CharField(source="subscription.user.username", read_only=True)

    class Meta:
        model = CreatorEarning
        fields = [
            "id",
            "listing",
            "listing_title",
            "subscription",
            "subscription_user",
            "gross_amount",
            "platform_fee",
            "net_amount",
            "status",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
