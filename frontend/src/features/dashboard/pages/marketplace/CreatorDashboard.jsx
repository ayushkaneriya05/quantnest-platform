import { useEffect, useMemo, useState } from "react";
import { DollarSign, RefreshCw, Sparkles, Star, Store } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Textarea } from "@/shared/components/ui/textarea";
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
import { strategyApi } from "@/shared/services/strategyApi";

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const emptyForm = {
  strategy: "",
  title: "",
  description: "",
  price: "0",
  is_free: false,
  subscription_type: "MONTHLY",
  min_capital_required: "0",
  is_featured: false,
  status: "ACTIVE",
};

export default function CreatorDashboard() {
  const { notify } = useNotifications();
  const [dashboard, setDashboard] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingListingId, setEditingListingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, strategiesRes] = await Promise.all([
        marketplaceApi.getCreatorDashboard(),
        strategyApi.getAll(),
      ]);
      const strategyRows = Array.isArray(strategiesRes?.results) ? strategiesRes.results : strategiesRes || [];
      setDashboard(dashboardRes.data || {});
      setStrategies(strategyRows);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load creator dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const listings = dashboard?.listings || [];
  const earnings = dashboard?.earnings || [];
  const reviews = dashboard?.reviews || [];
  const summary = dashboard?.summary || {};

  const listedStrategyIds = useMemo(
    () => new Set(listings.map((listing) => String(listing.strategy))),
    [listings],
  );

  const availableStrategies = strategies.filter(
    (strategy) => !listedStrategyIds.has(String(strategy.id)) || String(strategy.id) === String(form.strategy),
  );

  const openCreateDialog = () => {
    setEditingListingId(null);
    const firstStrategy = availableStrategies[0];
    setForm({
      ...emptyForm,
      strategy: firstStrategy ? String(firstStrategy.id) : "",
      title: firstStrategy?.name || "",
      description: firstStrategy?.description || "",
    });
    setDialogOpen(true);
  };

  const openEditDialog = (listing) => {
    setEditingListingId(listing.id);
    setForm({
      strategy: String(listing.strategy),
      title: listing.title || "",
      description: listing.description || "",
      price: String(listing.price || 0),
      is_free: Boolean(listing.is_free),
      subscription_type: listing.subscription_type || "MONTHLY",
      min_capital_required: String(listing.min_capital_required || 0),
      is_featured: Boolean(listing.is_featured),
      status: listing.status || "ACTIVE",
    });
    setDialogOpen(true);
  };

  const saveListing = async () => {
    try {
      setBusyAction("save-listing");
      const payload = {
        ...form,
        strategy: Number(form.strategy),
        price: form.is_free ? 0 : Number(form.price || 0),
        min_capital_required: Number(form.min_capital_required || 0),
      };
      if (editingListingId) {
        await marketplaceApi.updateListing(editingListingId, payload);
        notify.success("Marketplace listing updated");
      } else {
        await marketplaceApi.createListing(payload);
        notify.success("Marketplace listing published");
      }
      setDialogOpen(false);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || error?.response?.data?.error || "Failed to save listing");
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
      <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={openCreateDialog}>
        <Store className="mr-2 h-4 w-4" />
        Publish Strategy
      </Button>
    </>,
  );

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Listings", value: summary.listings || 0, tone: "text-white" },
          { label: "Subscribers", value: summary.subscribers || 0, tone: "text-cyan-300" },
          { label: "Pending Payout", value: `Rs ${formatCurrency(summary.pending_amount)}`, tone: "text-amber-300" },
          { label: "Lifetime Net", value: `Rs ${formatCurrency(summary.lifetime_net_amount)}`, tone: "text-emerald-300" },
        ].map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Loading creator dashboard...</CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="text-white">Your Listings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {listings.length === 0 ? (
                <div className="py-8 text-center text-gray-400">
                  No marketplace listings yet. Publish one of your strategies to start collecting subscribers.
                </div>
              ) : (
                listings.map((listing) => (
                  <div key={listing.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">{listing.title}</p>
                        <p className="mt-1 text-sm text-gray-400">
                          {listing.strategy_name} | {listing.subscription_type}
                        </p>
                      </div>
                      <Badge className="border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
                        {listing.status}
                      </Badge>
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
                      <div className="rounded-xl bg-gray-950/60 p-3">
                        <p className="text-gray-500">Price</p>
                        <p className="mt-1 text-white">
                          {listing.is_free ? "Free" : `Rs ${formatCurrency(listing.price)}`}
                        </p>
                      </div>
                      <div className="rounded-xl bg-gray-950/60 p-3">
                        <p className="text-gray-500">Subscribers</p>
                        <p className="mt-1 text-white">{listing.subscribers_count}</p>
                      </div>
                      <div className="rounded-xl bg-gray-950/60 p-3">
                        <p className="text-gray-500">Rating</p>
                        <p className="mt-1 text-white">{listing.avg_rating} / 5</p>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        className="border-gray-700 text-gray-100"
                        onClick={() => openEditDialog(listing)}
                      >
                        Edit Listing
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card className="border-gray-800 bg-gray-900/60">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <DollarSign className="h-4 w-4 text-emerald-300" />
                  Recent Earnings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {earnings.length === 0 ? (
                  <div className="py-8 text-center text-gray-400">No earnings recorded yet.</div>
                ) : (
                  earnings.slice(0, 6).map((earning) => (
                    <div key={earning.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                      <p className="font-semibold text-white">{earning.listing_title}</p>
                      <p className="mt-1 text-sm text-gray-400">Subscriber {earning.subscription_user}</p>
                      <p className="mt-3 text-sm text-gray-300">
                        Net Rs {formatCurrency(earning.net_amount)} | Fee Rs {formatCurrency(earning.platform_fee)}
                      </p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="border-gray-800 bg-gray-900/60">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Star className="h-4 w-4 text-amber-300" />
                  Recent Reviews
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {reviews.length === 0 ? (
                  <div className="py-8 text-center text-gray-400">No reviews yet.</div>
                ) : (
                  reviews.map((review) => (
                    <div key={review.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                      <p className="font-semibold text-white">{review.title || `${review.rating}/5 review`}</p>
                      <p className="mt-1 text-sm text-gray-400">{review.username}</p>
                      <p className="mt-2 text-sm text-gray-300">{review.comment || "No comment provided."}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-gray-800 bg-gray-950 text-white sm:max-w-2xl flex flex-col max-h-[85vh] gap-0 p-0">
          <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
            <DialogTitle>{editingListingId ? "Edit Marketplace Listing" : "Publish Strategy"}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-y-auto px-6 scrollbar-theme">
            <div className="grid gap-4 py-2 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Strategy</Label>
                <Select
                  value={form.strategy}
                  onValueChange={(value) => {
                    const strategy = strategies.find((row) => String(row.id) === value);
                    setForm((current) => ({
                      ...current,
                      strategy: value,
                      title: current.title || strategy?.name || "",
                      description: current.description || strategy?.description || "",
                    }));
                  }}
                  disabled={Boolean(editingListingId)}
                >
                  <SelectTrigger className="border-gray-700 bg-black/20 text-white">
                    <SelectValue placeholder="Select strategy" />
                  </SelectTrigger>
                  <SelectContent className="border-gray-800 bg-gray-900 text-white">
                    {availableStrategies.map((strategy) => (
                      <SelectItem key={strategy.id} value={String(strategy.id)}>
                        {strategy.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Plan Type</Label>
                <Select
                  value={form.subscription_type}
                  onValueChange={(value) => setForm((current) => ({ ...current, subscription_type: value }))}
                >
                  <SelectTrigger className="border-gray-700 bg-black/20 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="border-gray-800 bg-gray-900 text-white">
                    <SelectItem value="ONE_TIME">One-time</SelectItem>
                    <SelectItem value="MONTHLY">Monthly</SelectItem>
                    <SelectItem value="YEARLY">Yearly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label>Title</Label>
                <Input
                  value={form.title}
                  onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label>Description</Label>
                <Textarea
                  value={form.description}
                  onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label>Price (INR)</Label>
                <Input
                  type="number"
                  value={form.price}
                  onChange={(event) => setForm((current) => ({ ...current, price: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                  disabled={form.is_free}
                />
              </div>

              <div className="space-y-2">
                <Label>Minimum Capital</Label>
                <Input
                  type="number"
                  value={form.min_capital_required}
                  onChange={(event) => setForm((current) => ({ ...current, min_capital_required: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div>
                  <p className="text-sm font-medium text-white">Free Listing</p>
                  <p className="text-xs text-gray-400">Offer subscription without payment</p>
                </div>
                <Switch checked={form.is_free} onCheckedChange={(checked) => setForm((current) => ({ ...current, is_free: checked }))} />
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div>
                  <p className="text-sm font-medium text-white">Featured Badge</p>
                  <p className="text-xs text-gray-400">Highlight this listing in explore view</p>
                </div>
                <Switch checked={form.is_featured} onCheckedChange={(checked) => setForm((current) => ({ ...current, is_featured: checked }))} />
              </div>
            </div>
          </div>
          <DialogFooter className="px-6 pb-6 pt-4 shrink-0 border-t border-gray-800/50">
            <Button variant="outline" className="border-gray-700 text-gray-100" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={saveListing} disabled={busyAction === "save-listing" || !form.strategy}>
              <Sparkles className="mr-2 h-4 w-4" />
              {editingListingId ? "Save Changes" : "Publish"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
