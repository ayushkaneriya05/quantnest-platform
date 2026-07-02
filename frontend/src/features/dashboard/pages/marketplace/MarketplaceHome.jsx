import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, Search, Star, Store, Trophy } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { marketplaceApi } from "@/shared/services/marketplaceApi";

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const subscriptionTone = {
  ONE_TIME: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  MONTHLY: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
  YEARLY: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
};

export default function MarketplaceHome() {
  const { notify } = useNotifications();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: "",
    subscription_type: "ALL",
    featured: false,
  });
  const [busyAction, setBusyAction] = useState("");

  const loadListings = async (activeFilters = filters) => {
    try {
      setLoading(true);
      const params = {};
      if (activeFilters.search) params.search = activeFilters.search;
      if (activeFilters.subscription_type !== "ALL") {
        params.subscription_type = activeFilters.subscription_type;
      }
      if (activeFilters.featured) {
        params.featured = "true";
      }
      const response = await marketplaceApi.getListings(params);
      setListings(Array.isArray(response.data?.results) ? response.data.results : response.data || []);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load marketplace listings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadListings();
  }, []);

  const runSubscribe = async (listingId) => {
    try {
      setBusyAction(`subscribe-${listingId}`);
      await marketplaceApi.subscribe(listingId, false);
      notify.success("Strategy subscribed successfully");
      await loadListings();
    } catch (error) {
      notify.error(error?.response?.data?.detail || error?.response?.data?.error || "Subscription failed");
    } finally {
      setBusyAction("");
    }
  };

  useSetPageActions(
    <>
      <Button variant="outline" onClick={() => loadListings()} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button asChild className="bg-cyan-600 hover:bg-cyan-500">
        <Link to="/dashboard/marketplace/creator">
          <Store className="mr-2 h-4 w-4" />
          Creator Dashboard
        </Link>
      </Button>
    </>,
  );

  const summary = useMemo(
    () => ({
      total: listings.length,
      featured: listings.filter((item) => item.is_featured).length,
      free: listings.filter((item) => item.is_free).length,
      subscribed: listings.filter((item) => item.has_active_subscription).length,
    }),
    [listings],
  );

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Active Listings", value: summary.total, tone: "text-white" },
          { label: "Featured", value: summary.featured, tone: "text-amber-300" },
          { label: "Free Strategies", value: summary.free, tone: "text-emerald-300" },
          { label: "Your Subscriptions", value: summary.subscribed, tone: "text-cyan-300" },
        ].map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-gray-800 bg-gray-900/60">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1fr_220px_160px]">
          <div className="relative">
            <Search className="absolute left-3 top-3.5 h-4 w-4 text-gray-500" />
            <Input
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              placeholder="Search strategies, creators, or descriptions"
              className="border-gray-700 bg-black/20 pl-10 text-white"
            />
          </div>
          <Select
            value={filters.subscription_type}
            onValueChange={(value) => setFilters((current) => ({ ...current, subscription_type: value }))}
          >
            <SelectTrigger className="border-gray-700 bg-black/20 text-white">
              <SelectValue placeholder="Subscription type" />
            </SelectTrigger>
            <SelectContent className="border-gray-800 bg-gray-900 text-white">
              <SelectItem value="ALL">All plans</SelectItem>
              <SelectItem value="ONE_TIME">One-time</SelectItem>
              <SelectItem value="MONTHLY">Monthly</SelectItem>
              <SelectItem value="YEARLY">Yearly</SelectItem>
            </SelectContent>
          </Select>
          <Button
            className={filters.featured ? "bg-amber-600 hover:bg-amber-500" : "bg-gray-800 hover:bg-gray-700"}
            onClick={() => setFilters((current) => ({ ...current, featured: !current.featured }))}
          >
            <Star className="mr-2 h-4 w-4" />
            Featured only
          </Button>
        </CardContent>
        <CardContent className="px-5 pb-5 pt-0">
          <Button
            variant="outline"
            className="border-gray-700 text-gray-100"
            onClick={() => loadListings(filters)}
          >
            Apply Filters
          </Button>
        </CardContent>
      </Card>

      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Loading marketplace listings...</CardContent>
        </Card>
      ) : listings.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            No listings matched the current filters.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {listings.map((listing) => (
            <Card key={listing.id} className="border-gray-800 bg-gray-900/60">
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-white">{listing.title}</CardTitle>
                    <p className="mt-1 text-sm text-gray-400">
                      {listing.creator_name} | {listing.strategy_name}
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    {listing.is_featured ? (
                      <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">Featured</Badge>
                    ) : null}
                    {listing.is_verified ? (
                      <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">Verified</Badge>
                    ) : null}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <p className="text-sm leading-6 text-gray-300">
                  {listing.description || "No strategy description added yet."}
                </p>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Pricing</p>
                    <p className="mt-2 text-lg font-semibold text-white">
                      {listing.is_free ? "Free access" : `Rs ${formatCurrency(listing.price)}`}
                    </p>
                    <Badge className={`mt-2 ${subscriptionTone[listing.subscription_type] || subscriptionTone.MONTHLY}`}>
                      {listing.subscription_type.replace("_", " ")}
                    </Badge>
                  </div>
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Performance</p>
                    <p className="mt-2 text-sm text-white">
                      Backtest Sharpe {listing.backtest_sharpe}
                    </p>
                    <p className="mt-1 text-sm text-gray-400">
                      Expected DD {listing.expected_drawdown}% | Live Sharpe {listing.live_sharpe}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Subscribers</p>
                    <p className="mt-1 text-white">{listing.subscribers_count}</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Rating</p>
                    <p className="mt-1 text-white">{listing.avg_rating} / 5</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Reviews</p>
                    <p className="mt-1 text-white">{listing.total_reviews}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button asChild variant="outline" className="border-gray-700 text-gray-100">
                    <Link to={`/dashboard/marketplace/${listing.id}`}>
                      <Trophy className="mr-2 h-4 w-4" />
                      View Details
                    </Link>
                  </Button>
                  {listing.has_active_subscription ? (
                    <Button asChild className="bg-emerald-600 hover:bg-emerald-500">
                      <Link to="/dashboard/marketplace/subscriptions">Subscribed</Link>
                    </Button>
                  ) : (
                    <Button
                      className="bg-cyan-600 hover:bg-cyan-500"
                      onClick={() => runSubscribe(listing.id)}
                      disabled={busyAction === `subscribe-${listing.id}`}
                    >
                      Subscribe
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
