import { useEffect, useState } from "react";
import { MessageSquare, RefreshCw, ShieldCheck, XCircle } from "lucide-react";

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
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { marketplaceApi } from "@/shared/services/marketplaceApi";

const emptyReviewForm = {
  rating: 5,
  title: "",
  comment: "",
  use_duration_days: 0,
  would_recommend: true,
};

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function SubscriptionManager() {
  const { notify } = useNotifications();
  const [subscriptions, setSubscriptions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [activeSubscription, setActiveSubscription] = useState(null);
  const [activeReviewId, setActiveReviewId] = useState(null);
  const [reviewForm, setReviewForm] = useState(emptyReviewForm);

  const loadData = async () => {
    try {
      setLoading(true);
      const [subscriptionsRes, summaryRes] = await Promise.all([
        marketplaceApi.getSubscriptions(),
        marketplaceApi.getSubscriptionSummary(),
      ]);
      setSubscriptions(Array.isArray(subscriptionsRes.data?.results) ? subscriptionsRes.data.results : subscriptionsRes.data || []);
      setSummary(summaryRes.data || {});
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const cancelSubscription = async (id) => {
    try {
      setBusyAction(`cancel-${id}`);
      await marketplaceApi.cancelSubscription(id);
      notify.success("Subscription cancelled");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to cancel subscription");
    } finally {
      setBusyAction("");
    }
  };

  const openReviewDialog = async (subscription) => {
    try {
      setActiveSubscription(subscription);
      const reviewsRes = await marketplaceApi.getReviews({ listing: subscription.listing });
      const reviews = Array.isArray(reviewsRes.data?.results) ? reviewsRes.data.results : reviewsRes.data || [];
      const myReview = reviews.find((review) => review.is_owner);
      setActiveReviewId(myReview?.id || null);
      setReviewForm(
        myReview
          ? {
              rating: myReview.rating,
              title: myReview.title || "",
              comment: myReview.comment || "",
              use_duration_days: myReview.use_duration_days || 0,
              would_recommend: Boolean(myReview.would_recommend),
            }
          : emptyReviewForm,
      );
      setReviewDialogOpen(true);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load review data");
    }
  };

  const saveReview = async () => {
    if (!activeSubscription) return;
    try {
      setBusyAction("save-review");
      const payload = {
        listing: activeSubscription.listing,
        rating: Number(reviewForm.rating),
        title: reviewForm.title,
        comment: reviewForm.comment,
        use_duration_days: Number(reviewForm.use_duration_days || 0),
        would_recommend: reviewForm.would_recommend,
      };
      if (activeReviewId) {
        await marketplaceApi.updateReview(activeReviewId, payload);
        notify.success("Review updated");
      } else {
        await marketplaceApi.createReview(payload);
        notify.success("Review created");
      }
      setReviewDialogOpen(false);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to save review");
    } finally {
      setBusyAction("");
    }
  };

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Active", value: summary?.active || 0, tone: "text-emerald-300" },
          { label: "Inactive", value: summary?.inactive || 0, tone: "text-gray-200" },
          { label: "Auto Renew", value: summary?.auto_renew || 0, tone: "text-cyan-300" },
          { label: "Monthly Spend", value: `Rs ${formatCurrency(summary?.monthly_spend)}`, tone: "text-amber-300" },
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
          <CardContent className="py-12 text-center text-gray-400">Loading subscriptions...</CardContent>
        </Card>
      ) : subscriptions.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            No subscriptions yet. Explore the marketplace to follow a strategy.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {subscriptions.map((row) => (
            <Card key={row.id} className="border-gray-800 bg-gray-900/60">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-white">{row.listing_title}</CardTitle>
                    <p className="mt-1 text-sm text-gray-400">{row.listing_creator_name}</p>
                  </div>
                  <Badge className={row.is_active ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-gray-500/20 bg-gray-500/10 text-gray-200"}>
                    {row.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Plan</p>
                    <p className="mt-2 text-white">{row.subscription_type}</p>
                    <p className="mt-1 text-sm text-gray-400">Paid Rs {formatCurrency(row.amount_paid)}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Renewal</p>
                    <p className="mt-2 text-white">{row.auto_renew ? "Auto renew on" : "Manual renewal"}</p>
                    <p className="mt-1 text-sm text-gray-400">
                      {row.days_remaining == null ? "No expiry" : `${row.days_remaining} days remaining`}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl bg-gray-950/60 p-3 text-sm text-gray-400">
                  <p>Subscribed at <span className="text-white">{new Date(row.subscribed_at).toLocaleString("en-IN")}</span></p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    className="border-gray-700 text-gray-100"
                    onClick={() => openReviewDialog(row)}
                  >
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Write Review
                  </Button>
                  {row.is_active ? (
                    <Button
                      className="bg-red-600 hover:bg-red-500"
                      onClick={() => cancelSubscription(row.id)}
                      disabled={busyAction === `cancel-${row.id}`}
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
        <DialogContent className="border-gray-800 bg-gray-950 text-white flex flex-col max-h-[85vh] gap-0 p-0">
          <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
            <DialogTitle>Review Subscription</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-y-auto px-6 scrollbar-theme">
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Rating (1-5)</Label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={reviewForm.rating}
                  onChange={(event) => setReviewForm((current) => ({ ...current, rating: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label>Title</Label>
                <Input
                  value={reviewForm.title}
                  onChange={(event) => setReviewForm((current) => ({ ...current, title: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label>Comment</Label>
                <Textarea
                  value={reviewForm.comment}
                  onChange={(event) => setReviewForm((current) => ({ ...current, comment: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label>Use Duration (days)</Label>
                <Input
                  type="number"
                  min="0"
                  value={reviewForm.use_duration_days}
                  onChange={(event) => setReviewForm((current) => ({ ...current, use_duration_days: event.target.value }))}
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                  <div>
                    <p className="text-sm font-medium text-white">Would Recommend</p>
                    <p className="text-xs text-gray-400">Signal confidence in this strategy listing</p>
                  </div>
                </div>
                <Switch
                  checked={reviewForm.would_recommend}
                  onCheckedChange={(checked) => setReviewForm((current) => ({ ...current, would_recommend: checked }))}
                />
              </div>
            </div>
          </div>
          <DialogFooter className="px-6 pb-6 pt-4 shrink-0 border-t border-gray-800/50">
            <Button variant="outline" className="border-gray-700 text-gray-100" onClick={() => setReviewDialogOpen(false)}>
              Cancel
            </Button>
            <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={saveReview} disabled={busyAction === "save-review"}>
              Save Review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
