from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from strategies.models import Strategy

from .models import CreatorEarning, MarketplaceListing, StrategyReview, Subscription
from .serializers import (
    CreatorEarningSerializer,
    MarketplaceListingSerializer,
    StrategyReviewSerializer,
    SubscriptionSerializer,
)
from .services import MarketplaceService


class MarketplaceListingViewSet(viewsets.ModelViewSet):
    serializer_class = MarketplaceListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MarketplaceListing.objects.select_related("strategy", "creator")
        request = self.request
        if self.action in {"create", "update", "partial_update", "destroy", "my_listings"}:
            return qs.filter(creator=request.user)
        if self.action == "retrieve":
            return qs.filter(status__in=["ACTIVE", "PENDING"]).distinct()

        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        featured = request.query_params.get("featured")
        subscription_type = request.query_params.get("subscription_type")

        qs = qs.filter(status="ACTIVE")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(description__icontains=search) | qs.filter(strategy__name__icontains=search)
        if featured == "true":
            qs = qs.filter(is_featured=True)
        if subscription_type:
            qs = qs.filter(subscription_type=subscription_type)
        return qs.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        strategy_id = request.data.get("strategy")
        strategy = Strategy.objects.get(id=strategy_id, user=request.user)
        listing = MarketplaceService.publish_listing(request.user, strategy, request.data)
        serializer = self.get_serializer(listing)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        listing = self.get_object()
        updated = MarketplaceService.publish_listing(request.user, listing.strategy, {**self.get_serializer(listing).data, **request.data})
        serializer = self.get_serializer(updated)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my-listings")
    def my_listings(self, request):
        listings = MarketplaceListing.objects.filter(creator=request.user).select_related("strategy", "creator")
        data = self.get_serializer(listings, many=True).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="creator-dashboard")
    def creator_dashboard(self, request):
        payload = MarketplaceService.creator_dashboard(request.user)
        return Response(
            {
                "summary": payload["summary"],
                "listings": self.get_serializer(payload["listings"], many=True).data,
                "earnings": CreatorEarningSerializer(payload["earnings"], many=True).data,
                "reviews": StrategyReviewSerializer(payload["reviews"], many=True, context=self.get_serializer_context()).data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        listing = self.get_object()
        if listing.status != "ACTIVE" and listing.creator_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = MarketplaceService.listing_detail_payload(listing, request.user)
        return Response(
            {
                "listing": self.get_serializer(payload["listing"]).data,
                "reviews": StrategyReviewSerializer(payload["reviews"], many=True, context=self.get_serializer_context()).data,
                "latest_snapshot": {
                    "date": payload["latest_snapshot"].date,
                    "daily_pnl": payload["latest_snapshot"].daily_pnl,
                    "cumulative_pnl": payload["latest_snapshot"].cumulative_pnl,
                    "trades_count": payload["latest_snapshot"].trades_count,
                    "win_rate": payload["latest_snapshot"].win_rate,
                    "avg_trade_pnl": payload["latest_snapshot"].avg_trade_pnl,
                    "max_drawdown_pct": payload["latest_snapshot"].max_drawdown_pct,
                    "sharpe_ratio_30d": payload["latest_snapshot"].sharpe_ratio_30d,
                }
                if payload["latest_snapshot"]
                else None,
                "active_subscription": SubscriptionSerializer(payload["active_subscription"]).data
                if payload["active_subscription"]
                else None,
                "my_review": StrategyReviewSerializer(payload["my_review"], context=self.get_serializer_context()).data
                if payload["my_review"]
                else None,
            }
        )


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related("listing", "listing__creator")

    @action(detail=False, methods=["post"])
    def subscribe(self, request):
        listing = MarketplaceListing.objects.get(id=request.data.get("listing"), status="ACTIVE")
        sub = MarketplaceService.subscribe(
            request.user,
            listing,
            auto_renew=bool(request.data.get("auto_renew")),
        )
        return Response(self.get_serializer(sub).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(MarketplaceService.subscription_summary(request.user))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sub = self.get_object()
        MarketplaceService.cancel_subscription(sub)
        return Response(self.get_serializer(sub).data)


class StrategyReviewViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = StrategyReview.objects.filter(listing__status="ACTIVE").select_related("listing", "user")
        listing_id = self.request.query_params.get("listing")
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        listing = serializer.validated_data["listing"]
        verified = Subscription.objects.filter(
            user=self.request.user,
            listing=listing,
            is_active=True,
        ).exists()
        review = serializer.save(user=self.request.user, is_verified_purchase=verified)
        MarketplaceService.refresh_listing_rating(review.listing)

    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        if review.user_id != request.user.id:
            return Response({"detail": "You can only edit your own review."}, status=status.HTTP_403_FORBIDDEN)
        response = super().partial_update(request, *args, **kwargs)
        MarketplaceService.refresh_listing_rating(review.listing)
        return response

    @action(detail=True, methods=["post"])
    def helpful(self, request, pk=None):
        review = self.get_object()
        review.helpful_count += 1
        review.save(update_fields=["helpful_count", "updated_at"])
        return Response(self.get_serializer(review).data)


class CreatorEarningViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreatorEarningSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CreatorEarning.objects.filter(creator=self.request.user).select_related("listing", "subscription", "subscription__user")
