import { useEffect, useMemo, useState } from "react";
import { BookOpen, Lightbulb, PencilLine, Plus, RefreshCw, Sparkles } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Textarea } from "@/shared/components/ui/textarea";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { analyticsSuiteApi } from "@/shared/services/analyticsSuiteApi";

const defaultForm = {
  title: "",
  notes: "",
  lessons_learned: "",
  emotion_before: "",
  emotion_after: "",
  setup_quality: 3,
  execution_quality: 3,
  rule_followed: true,
  mistake_tags: [],
};

export default function TradeJournal() {
  const { notify } = useNotifications();
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState({});
  const [insights, setInsights] = useState([]);
  const [tags, setTags] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [entriesRes, summaryRes, insightsRes, tagsRes] = await Promise.all([
        analyticsSuiteApi.getJournalEntries(),
        analyticsSuiteApi.getJournalSummary(),
        analyticsSuiteApi.getInsights(),
        analyticsSuiteApi.getMistakeTags(),
      ]);
      setEntries(Array.isArray(entriesRes.data?.results) ? entriesRes.data.results : entriesRes.data || []);
      setSummary(summaryRes.data || {});
      setInsights(Array.isArray(insightsRes.data?.results) ? insightsRes.data.results : insightsRes.data || []);
      setTags(Array.isArray(tagsRes.data?.results) ? tagsRes.data.results : tagsRes.data || []);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load trade journal");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(defaultForm);
    setOpen(true);
  };

  const openEdit = (entry) => {
    setEditing(entry);
    setForm({
      title: entry.title || "",
      notes: entry.notes || "",
      lessons_learned: entry.lessons_learned || "",
      emotion_before: entry.emotion_before || "",
      emotion_after: entry.emotion_after || "",
      setup_quality: entry.setup_quality || 3,
      execution_quality: entry.execution_quality || 3,
      rule_followed: entry.rule_followed ?? true,
      mistake_tags: entry.mistake_tags || [],
    });
    setOpen(true);
  };

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button
        variant="outline"
        className="border-gray-700 text-gray-100"
        onClick={async () => {
          try {
            setBusy("bootstrap");
            await analyticsSuiteApi.bootstrapJournalEntries();
            notify.success("Journal entries created from recent paper and live trades");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to bootstrap journal entries");
          } finally {
            setBusy("");
          }
        }}
      >
        <BookOpen className="mr-2 h-4 w-4" />
        Bootstrap Entries
      </Button>
      <Button
        variant="outline"
        className="border-gray-700 text-gray-100"
        onClick={async () => {
          try {
            setBusy("insights");
            await analyticsSuiteApi.generateInsights();
            notify.success("Journal insights generated");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to generate insights");
          } finally {
            setBusy("");
          }
        }}
      >
        <Sparkles className="mr-2 h-4 w-4" />
        Generate Insights
      </Button>
      <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={openCreate}>
        <Plus className="mr-2 h-4 w-4" />
        New Entry
      </Button>
    </>,
  );

  const saveEntry = async () => {
    try {
      const payload = {
        ...form,
        setup_quality: Number(form.setup_quality),
        execution_quality: Number(form.execution_quality),
      };
      if (editing) {
        await analyticsSuiteApi.updateJournalEntry(editing.id, payload);
        notify.success("Journal entry updated");
      } else {
        await analyticsSuiteApi.createJournalEntry(payload);
        notify.success("Journal entry created");
      }
      setOpen(false);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to save journal entry");
    }
  };

  const summaryCards = [
    { label: "Entries", value: summary.entries || 0, tone: "text-white" },
    { label: "Rule Follow Rate", value: `${summary.rule_follow_rate || 0}%`, tone: "text-emerald-300" },
    { label: "Setup Quality", value: `${summary.avg_setup_quality || 0}/5`, tone: "text-cyan-300" },
    { label: "Insights", value: summary.insights || 0, tone: "text-amber-300" },
  ];

  const suggestedTags = useMemo(() => tags.map((tag) => tag.name), [tags]);

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader><CardTitle className="text-white">Journal Entries</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-8 text-center text-gray-400">Loading journal entries...</div>
            ) : entries.length === 0 ? (
              <div className="py-8 text-center text-gray-400">No journal entries yet.</div>
            ) : (
              entries.slice(0, 12).map((entry) => (
                <div key={entry.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{entry.title}</p>
                      <p className="mt-1 text-sm text-gray-400">{entry.strategy_name || "No strategy"} • {entry.symbol || "-"} • {entry.trade_source}</p>
                    </div>
                    <Button size="sm" variant="outline" className="border-gray-700 text-gray-100" onClick={() => openEdit(entry)}>
                      <PencilLine className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20">Setup {entry.setup_quality}/5</Badge>
                    <Badge className="bg-indigo-500/10 text-indigo-300 border-indigo-500/20">Execution {entry.execution_quality}/5</Badge>
                    <Badge className={entry.rule_followed ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" : "bg-red-500/10 text-red-300 border-red-500/20"}>
                      {entry.rule_followed ? "Rules followed" : "Rule break"}
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm text-gray-300">{entry.notes || entry.lessons_learned || "No notes yet."}</p>
                  {(entry.mistake_tags || []).length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {entry.mistake_tags.map((tag) => (
                        <Badge key={`${entry.id}-${tag}`} className="bg-amber-500/10 text-amber-300 border-amber-500/20">{tag}</Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader><CardTitle className="flex items-center gap-2 text-white"><Lightbulb className="h-4 w-4 text-amber-300" /> Generated Insights</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {insights.length === 0 && !loading ? (
              <div className="py-8 text-center text-gray-400">Generate insights after creating or bootstrapping journal entries.</div>
            ) : (
              insights.map((insight) => (
                <div key={insight.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <p className="font-semibold text-white">{insight.title}</p>
                  <p className="mt-2 text-sm text-gray-300">{insight.description}</p>
                </div>
              ))
            )}

            {suggestedTags.length ? (
              <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <p className="text-sm font-medium text-white">Available mistake tags</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {suggestedTags.map((tag) => (
                    <Badge key={tag} className="bg-gray-500/10 text-gray-200 border-gray-500/20">{tag}</Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-gray-800 bg-gray-950 text-white sm:max-w-2xl flex flex-col max-h-[85vh] gap-0 p-0">
          <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
            <DialogTitle>{editing ? "Edit Journal Entry" : "New Journal Entry"}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-y-auto px-6 scrollbar-theme">
            <div className="grid gap-4 py-2 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label>Title</Label>
                <Input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2">
                <Label>Emotion Before</Label>
                <Input value={form.emotion_before} onChange={(event) => setForm((current) => ({ ...current, emotion_before: event.target.value }))} className="border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2">
                <Label>Emotion After</Label>
                <Input value={form.emotion_after} onChange={(event) => setForm((current) => ({ ...current, emotion_after: event.target.value }))} className="border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2">
                <Label>Setup Quality (1-5)</Label>
                <Input type="number" min="1" max="5" value={form.setup_quality} onChange={(event) => setForm((current) => ({ ...current, setup_quality: event.target.value }))} className="border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2">
                <Label>Execution Quality (1-5)</Label>
                <Input type="number" min="1" max="5" value={form.execution_quality} onChange={(event) => setForm((current) => ({ ...current, execution_quality: event.target.value }))} className="border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div>
                    <Label>Rule Followed</Label>
                    <p className="text-xs text-gray-500">Mark whether the trade followed the intended strategy rules.</p>
                  </div>
                  <Switch checked={Boolean(form.rule_followed)} onCheckedChange={(value) => setForm((current) => ({ ...current, rule_followed: value }))} />
                </div>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Notes</Label>
                <Textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} className="min-h-24 border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Lessons Learned</Label>
                <Textarea value={form.lessons_learned} onChange={(event) => setForm((current) => ({ ...current, lessons_learned: event.target.value }))} className="min-h-24 border-gray-700 bg-black/20 text-white" />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label>Mistake Tags (comma separated)</Label>
                <Input
                  value={(form.mistake_tags || []).join(", ")}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      mistake_tags: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
                    }))
                  }
                  className="border-gray-700 bg-black/20 text-white"
                />
              </div>
            </div>
          </div>
          <DialogFooter className="px-6 pb-6 pt-4 shrink-0 border-t border-gray-800/50">
            <Button variant="outline" className="border-gray-700 text-gray-100" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={saveEntry}>Save Entry</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
