import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PropTypes from "prop-types";
import { Sparkles, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { journalApi } from "@/shared/services/journalApi";
import { executionReportsApi } from "@/shared/services/executionReportsApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatDateTime } from "@/shared/utils/formatters";
import { displayMoney, pnlTone, modes } from "@/features/journal/hooks/useReviewWorkspace.js";

const tradeFields = { TERMINAL: "terminal_trade", PAPER: "paper_trade", LIVE: "live_trade" };

export default function TradeReviewDialog({ trade, filters, tags = [], onClose, onSaved }) {
  const review = trade.review;
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [form, setForm] = useState({ title: review?.title || `${trade.symbol} trade review`, notes: review?.notes || "",
    lessons_learned: review?.lessons_learned || "", execution_quality: review?.execution_quality ?? null, mistake_tags: review?.mistake_tags || [] });
  const [customTag, setCustomTag] = useState("");
  const [includeNotes, setIncludeNotes] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (key, value) => setForm((previous) => ({ ...previous, [key]: value }));
  async function save() {
    setBusy(true); setError("");
    try {
      if (review) await journalApi.update(review.id, form);
      else await journalApi.create({ ...form, source: trade.source, [tradeFields[trade.source]]: trade.id });
      notify.success("Trade review saved"); onSaved(); onClose();
    } catch (error) { setError(getApiErrorMessage(error, "Could not save the review")); }
    finally { setBusy(false); }
  }
  async function research() {
    setBusy(true); setError("");
    try {
      const { data } = await executionReportsApi.researchContext({ filters, trade_id: trade.id, include_notes: includeNotes });
      navigate(`/research?session=${data.id}&review=1`);
    } catch (error) { setError(getApiErrorMessage(error, "Could not attach this trade to research")); }
    finally { setBusy(false); }
  }
  return <Dialog open onOpenChange={(open) => { if (!open && !busy) onClose(); }}><DialogContent className="flex max-h-[calc(100dvh_-_2rem)] w-[calc(100%_-_2rem)] flex-col gap-0 overflow-hidden rounded-xl p-0 sm:max-w-3xl">
    <div className="shrink-0 border-b border-border px-5 py-4 pr-12"><DialogTitle>{trade.symbol} · {trade.source.toLowerCase()} review</DialogTitle><DialogDescription className="mt-2">Execution details are read-only. Notes and ratings are your own assessment.</DialogDescription></div>
    <div className="scrollbar-theme min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
      <div className="grid gap-3 rounded-xl border border-border bg-card/50 p-4 sm:grid-cols-2">
        <div><p className="text-xs text-muted-foreground">Entry → exit</p><p className="mt-1 text-xs">{formatDateTime(trade.entry_time)} → {formatDateTime(trade.exit_time)}</p></div>
        <div><p className="text-xs text-muted-foreground">Realized P&L</p><p className={`mt-1 font-semibold ${pnlTone(trade.pnl)}`}>{displayMoney(trade.pnl)}</p></div>
        <div><p className="text-xs text-muted-foreground">Execution</p><p className="mt-1 text-sm">{trade.side} · {trade.quantity} units · {displayMoney(trade.entry_price)} → {displayMoney(trade.exit_price)}</p></div>
        <div><p className="text-xs text-muted-foreground">Exit reason</p><p className="mt-1 text-sm">{trade.exit_reason || "Not recorded"}</p></div>
        <p className="text-xs text-muted-foreground sm:col-span-2">{modes.find((mode) => mode.value === trade.source).description}</p>
      </div>
      <div className="space-y-2"><Label htmlFor="review-title">Title</Label><Input id="review-title" maxLength={200} value={form.title} onChange={(event) => set("title", event.target.value)} /></div>
      <div className="space-y-2"><Label htmlFor="review-notes">Trade notes</Label><Textarea id="review-notes" maxLength={12000} rows={4} placeholder="Describe the setup, execution, and what you noticed…" value={form.notes} onChange={(event) => set("notes", event.target.value)} /></div>
      <div className="space-y-2"><Label htmlFor="review-lessons">Lessons learned</Label><Textarea id="review-lessons" maxLength={6000} rows={3} placeholder="What would you repeat or change?" value={form.lessons_learned} onChange={(event) => set("lessons_learned", event.target.value)} /></div>
      <div className="space-y-2"><Label>Execution rating · optional</Label><Select value={form.execution_quality == null ? "none" : String(form.execution_quality)} onValueChange={(value) => set("execution_quality", value === "none" ? null : Number(value))}>
        <SelectTrigger aria-label="Execution rating"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Not rated</SelectItem>{[1, 2, 3, 4, 5].map((value) => <SelectItem key={value} value={String(value)}>{value} / 5</SelectItem>)}</SelectContent>
      </Select></div>
      <div className="space-y-3"><Label>Mistake tags · optional</Label><div className="flex flex-wrap gap-2">
        {[...new Set([...tags, ...form.mistake_tags])].map((tag) => <button key={tag} type="button" aria-pressed={form.mistake_tags.includes(tag)}
          disabled={!form.mistake_tags.includes(tag) && form.mistake_tags.length >= 12}
          onClick={() => set("mistake_tags", form.mistake_tags.includes(tag) ? form.mistake_tags.filter((value) => value !== tag) : [...form.mistake_tags, tag])}
          className={`rounded-full border px-3 py-1.5 text-xs ${form.mistake_tags.includes(tag) ? "border-indigo-400/50 bg-indigo-500/15 text-indigo-700 dark:text-indigo-200" : "border-border text-muted-foreground hover:text-foreground"}`}>{tag}</button>)}
      </div><form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); if (customTag.trim() && form.mistake_tags.length < 12 && !form.mistake_tags.includes(customTag.trim())) set("mistake_tags", [...form.mistake_tags, customTag.trim()]); setCustomTag(""); }}>
        <Input aria-label="Custom mistake tag" maxLength={60} placeholder="Add your own tag…" value={customTag} onChange={(event) => setCustomTag(event.target.value)} /><Button variant="outline" type="submit" disabled={!customTag.trim() || form.mistake_tags.length >= 12}>Add</Button>
      </form></div>
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
        <label className="flex items-center gap-2 text-xs text-foreground"><Checkbox checked={includeNotes} onCheckedChange={(value) => setIncludeNotes(Boolean(value))} />Include saved journal notes in AI research</label>
        <Button variant="ghost" className="mt-2 text-indigo-700 dark:text-indigo-300" onClick={research} disabled={busy}><Sparkles size={15} className="mr-2" />Ask AI about this trade</Button>
        <p className="text-xs text-muted-foreground">Opens a conversation with recorded evidence. Sending the question starts research.</p>
      </div>
      {error && <p role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
    </div>
    <div className="flex shrink-0 justify-end gap-3 border-t border-border bg-background px-5 py-4"><Button variant="outline" onClick={onClose} disabled={busy}>Close</Button><Button disabled={busy || !form.title.trim()} onClick={save}>{busy && <Loader2 size={15} className="mr-2 animate-spin" />}Save review</Button></div>
  </DialogContent></Dialog>;
}
TradeReviewDialog.propTypes = { trade: PropTypes.object.isRequired, filters: PropTypes.object.isRequired, tags: PropTypes.array, onClose: PropTypes.func.isRequired, onSaved: PropTypes.func.isRequired };
