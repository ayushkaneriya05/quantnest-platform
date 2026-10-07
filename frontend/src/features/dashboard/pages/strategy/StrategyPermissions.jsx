import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Copy, ExternalLink, Lock, Globe, Share2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useEnums } from "@/shared/context/EnumsContext";
import { usePageActions } from "@/shared/context/pageActions";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { strategyApi } from "@/shared/services/strategyApi";
import StrategyConfigNav from "./StrategyConfigNav";
import StrategyFooter from "./StrategyFooter";

export default function StrategyPermissions() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions();
  const [strategy, setStrategy] = useState(null);
  const [visibility, setVisibility] = useState("PRIVATE");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await strategyApi.getById(id);
      setStrategy(data);
      setVisibility(data.visibility);
    } catch (failure) { setError(getApiErrorMessage(failure, "Could not load sharing settings.")); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);
  const save = async () => {
    setSaving(true);
    try {
      const data = await strategyApi.update(id, { visibility });
      setStrategy(data);
      setVisibility(data.visibility);
      setCopied(false);
      notify.success(data.visibility === "PUBLIC" ? "Read-only share link enabled." : "Strategy is private. The share link is disabled.");
    } catch (failure) { notify.error(getApiErrorMessage(failure, "Could not save sharing settings.")); }
    finally { setSaving(false); }
  };
  const link = `${window.location.origin}/strategy/view/${id}`;
  const copy = async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(link);
      setCopied(true);
      notify.success("Share link copied.");
    } catch { notify.error("Could not copy the link. Select it and copy it manually."); }
  };
  if (loading) return <div className="flex h-64 items-center justify-center"><GlobalLoader /></div>;
  if (error) return <div className="container-padding space-y-4 py-8"><p role="alert" className="text-rose-300">{error}</p><Button onClick={load}>Retry</Button></div>;
  const isPublic = strategy?.visibility === "PUBLIC";
  const dirty = visibility !== strategy?.visibility;
  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="scrollbar-theme flex-1 overflow-y-auto"><div className="container-padding space-y-6 py-6">
      <section className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 sm:p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Share2 className="h-5 w-5 text-slate-300" />Strategy sharing</h2>
        <p className="mt-2 text-sm text-slate-400">Choose who can view your current strategy configuration.</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2" role="group" aria-label="Strategy visibility">
          {(enums.StrategyVisibility || []).map((option) => {
            const Icon = option.value === "PUBLIC" ? Globe : Lock;
            return <button type="button" key={option.value} aria-pressed={visibility === option.value} disabled={saving}
              onClick={() => setVisibility(option.value)}
              className={`rounded-xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${visibility === option.value ? "border-slate-400 bg-slate-800/70" : "border-slate-800 hover:bg-slate-900"}`}>
              <span className="flex items-center gap-2 font-medium"><Icon className="h-4 w-4" />{option.label}</span>
              <span className="mt-2 block text-sm text-slate-400">{option.value === "PUBLIC" ? "Anyone with the link can view the rules and settings." : "Only you can access this strategy."}</span>
            </button>;
          })}
        </div>
        {dirty && <p className="mt-4 text-sm text-amber-300" role="status">Save changes to update link access.</p>}
      </section>
      <section className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 sm:p-6">
        <h3 className="text-base font-semibold">Share link</h3>
        {isPublic ? <>
          <p className="mb-4 mt-2 text-sm text-slate-400">This link shows the current saved rules, instruments, and settings. Trading results and account details stay private.</p>
          <div className="flex flex-wrap gap-2">
            <Input className="min-w-0 flex-1 font-mono text-sm" value={link} readOnly aria-label="Strategy share link" onFocus={(event) => event.target.select()} />
            <Button variant="outline" onClick={copy} aria-label="Copy share link"><Copy />{copied ? "Copied" : "Copy"}</Button>
            <Button variant="outline" asChild><a href={link} target="_blank" rel="noopener noreferrer"><ExternalLink />Preview</a></Button>
          </div>
          <p className="mt-3 text-xs text-slate-500">Save Private visibility to disable access immediately.</p>
        </> : <p className="mt-2 text-sm text-slate-400">The link is disabled. Select Public and save to enable read-only sharing.</p>}
      </section>
    </div></div>
    <StrategyFooter onSave={save} onCancel={() => navigate("/dashboard/strategy/list")} saving={saving} saveLabel="Save sharing" savingLabel="Saving…" />
  </div>;
}
