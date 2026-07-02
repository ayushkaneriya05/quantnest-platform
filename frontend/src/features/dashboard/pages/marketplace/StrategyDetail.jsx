import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RefreshCw, ShieldCheck, Star, TrendingUp } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { marketplaceApi } from "@/shared/services/marketplaceApi";

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function StrategyDetail() {
  const { id } = useParams();
  const { notify } = useNotifications();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await marketplaceApi.getListingDetail(id);
      setPayload(response.data || null);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load listing details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const listing = payload?.listing;
  const reviews = payload?.reviews || [];
  const latestSnapshot = payload?.latest_snapshot;
  const activeSubscription = payload?.active_subscription;

  const subscribe = async () => {
    try {
      setBusyAction("subscribe");
      await marketplaceApi.subscribe(Number(id), false);
      notify.success("Strategy subscribed successfully");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || error?.response?.data?.error || "Subscription failed");
    } finally {
      setBusyAction("");
    }
  };

  const markHelpful = async (reviewId) => {
    try {
      setBusyAction(`helpful-${reviewId}`);
      await marketplaceApi.markReviewHelpful(reviewId);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to mark review helpful");
    } finally {
      setBusyAction("");
    }
  };

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      {activeSubscription ? (
        <Button asChild className="bg-emerald-600 hover:bg-emerald-500">
          <Link to="/dashboard/marketplace/subscriptions">Subscribed</Link>
        </Button>
      ) : (
        <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={subscribe} disabled={busyAction === "subscribe"}>
          Subscribe
        </Button>
      )}
    </>,
  );

  if (loading) {
    return (
      <div className="container-padding py-6 lg:py-8">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Loading listing details...</CardContent>
        </Card>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="container-padding py-6 lg:py-8">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Listing not found.</CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="text-2xl text-white">{listing.title}</CardTitle>
              <p className="mt-2 text-sm text-gray-400">
                {listing.creator_name} | {listing.strategy_name}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {listing.is_verified ? (
                <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">Verified</Badge>
              ) : null}
              {listing.is_featured ? (
                <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">Featured</Badge>
              ) : null}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="text-sm leading-7 text-gray-300">{listing.description || "No description provided."}</p>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Pricing</p>
              <p className="mt-2 text-lg font-semibold text-white">
                {listing.is_free ? "Free access" : `Rs ${formatCurrency(listing.price)}`}
              </p>
              <p className="mt-1 text-sm text-gray-400">{listing.subscription_type}</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Backtest Sharpe</p>
              <p className="mt-2 text-lg font-semibold text-cyan-300">{listing.backtest_sharpe}</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Expected Drawdown</p>
              <p className="mt-2 text-lg font-semibold text-amber-300">{listing.expected_drawdown}%</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Subscribers</p>
              <p className="mt-2 text-lg font-semibold text-white">{listing.subscribers_count}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <TrendingUp className="h-4 w-4 text-cyan-300" />
              Latest Performance Snapshot
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {latestSnapshot ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Snapshot Date</p>
                    <p className="mt-1 text-white">{latestSnapshot.date}</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">30D Sharpe</p>
                    <p className="mt-1 text-white">{latestSnapshot.sharpe_ratio_30d}</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Win Rate</p>
                    <p className="mt-1 text-white">{latestSnapshot.win_rate}%</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Trades</p>
                    <p className="mt-1 text-white">{latestSnapshot.trades_count}</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-gray-800 bg-black/20 p-4 text-sm text-gray-300">
                  Cumulative P&L {latestSnapshot.cumulative_pnl} | Average trade P&L {latestSnapshot.avg_trade_pnl}
                </div>
              </>
            ) : (
              <div className="py-8 text-center text-gray-400">
                No performance snapshot available yet for this strategy.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              Access Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeSubscription ? (
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                <p className="font-semibold">You are subscribed to this listing</p>
                <p className="mt-2">
                  {activeSubscription.days_remaining == null
                    ? "This plan has no expiry."
                    : `${activeSubscription.days_remaining} days remaining on your subscription.`}
                </p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-800 bg-black/20 p-4 text-sm text-gray-300">
                Subscribe to track this strategy inside your marketplace subscriptions and review it as a verified user.
              </div>
            )}
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4 text-sm text-gray-300">
              Rating {listing.avg_rating} / 5 from {listing.total_reviews} reviews.
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Star className="h-4 w-4 text-amber-300" />
            Reviews
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {reviews.length === 0 ? (
            <div className="py-8 text-center text-gray-400">No reviews yet for this listing.</div>
          ) : (
            reviews.map((review) => (
              <div key={review.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-white">{review.title || `${review.rating}/5 review`}</p>
                    <p className="mt-1 text-sm text-gray-400">{review.username}</p>
                  </div>
                  {review.is_verified_purchase ? (
                    <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">Verified purchase</Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm leading-6 text-gray-300">{review.comment || "No written feedback."}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    className="border-gray-700 text-gray-100"
                    onClick={() => markHelpful(review.id)}
                    disabled={busyAction === `helpful-${review.id}`}
                  >
                    Helpful ({review.helpful_count})
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
