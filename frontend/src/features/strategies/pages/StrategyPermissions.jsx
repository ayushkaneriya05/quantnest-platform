import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Copy, ExternalLink, Lock, Globe, Share2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useEnums } from "@/shared/context/EnumsContext";
import { usePageActions } from "@/shared/context/pageActions";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { strategyApi } from "@/shared/services/strategyApi";
import StrategyConfigNav from "@/features/strategies/components/StrategyConfigNav.jsx";
import StrategyFooter from "@/features/strategies/components/StrategyFooter.jsx";

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
  if (error) return <div className="page-content"><p role="alert" className="text-loss">{error}</p><Button className="justify-self-start" onClick={load}>Retry</Button></div>;
  const isPublic = strategy?.visibility === "PUBLIC";
  const dirty = visibility !== strategy?.visibility;
  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="scrollbar-theme flex-1 overflow-y-auto"><div className="page-content">
      <section className="rounded-xl border border-border bg-background/50 p-3 sm:p-4">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Share2 className="h-5 w-5 text-foreground" />Strategy sharing</h2>
        <p className="mt-2 text-sm text-muted-foreground">Choose who can view your current strategy configuration.</p>
        <div role="group" aria-label="Strategy visibility" className="mt-3 grid gap-3 sm:grid-cols-2">
          {(enums.StrategyVisibility || []).map((option) => {
            const Icon = option.value === "PUBLIC" ? Globe : Lock;
            const selected = visibility === option.value;
            return <Button key={option.value} variant={selected ? "selected" : "outline"} type="button"
              aria-pressed={selected} aria-label={option.label} disabled={saving} onClick={() => setVisibility(option.value)}
              className="block h-auto whitespace-normal p-3 text-left">
              <span className="flex items-center gap-2">
                <Icon aria-hidden="true" className={`h-4 w-4 ${selected ? "text-brand" : "text-muted-foreground"}`} />
                <span className="font-medium">{option.label}</span>
              </span>
              <span className="mt-2 block text-sm text-muted-foreground">{option.value === "PUBLIC" ? "Anyone with the link can view the rules and settings." : "Only you can access this strategy."}</span>
            </Button>;
          })}
        </div>
        {dirty && <p className="mt-3 text-sm text-warning" role="status">Save changes to update link access.</p>}
      </section>
      <section className="rounded-xl border border-border bg-background/50 p-3 sm:p-4">
        <h3 className="text-base font-semibold">Share link</h3>
        {isPublic ? <>
          <p className="mb-3 mt-2 text-sm text-muted-foreground">This link shows the current saved rules, instruments, and settings. Trading results and account details stay private.</p>
          <div className="flex flex-wrap gap-2">
            <Input className="min-w-0 flex-1 font-mono text-sm" value={link} readOnly aria-label="Strategy share link" onFocus={(event) => event.target.select()} />
            <Button variant="outline" onClick={copy} aria-label="Copy share link"><Copy />{copied ? "Copied" : "Copy"}</Button>
            <Button variant="outline" asChild><a href={link} target="_blank" rel="noopener noreferrer"><ExternalLink />Preview</a></Button>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Save Private visibility to disable access immediately.</p>
        </> : <p className="mt-2 text-sm text-muted-foreground">The link is disabled. Select Public and save to enable read-only sharing.</p>}
      </section>
    </div></div>
    <StrategyFooter onSave={save} onCancel={() => navigate("/strategies")} saving={saving} disabled={!dirty} saveLabel="Save sharing" savingLabel="Saving…" />
  </div>;
}
