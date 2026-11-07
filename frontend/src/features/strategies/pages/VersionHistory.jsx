import Pagination from "@/shared/components/Pagination";
import { usePagination } from "@/shared/hooks/usePagination";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { History, RotateCcw, Eye, GitBranch } from "lucide-react";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { formatDateTime } from "@/shared/utils/formatters";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Switch } from "@/shared/components/ui/switch";
import { Badge } from "@/shared/components/ui/badge";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/pageActions";
import { customConfirm, customPrompt } from "@/shared/components/ui/custom-dialog";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import StrategyConfigNav from "../components/StrategyConfigNav";
import StrategySnapshotViewer from "../components/StrategySnapshotViewer";

export default function VersionHistory() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { setPageHeader, setPageActions } = usePageActions();
  const [strategy, setStrategy] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const inFlight = useRef(false);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(String(id), 'versions');
  const [metadata, setMetadata] = useState({ count: 0 });
  const generation = useRef(0);
  const previewRequest = useRef(0);
  const [previewLoading, setPreviewLoading] = useState(false);
  const preview = async version => {
    const request = ++previewRequest.current;
    setSelectedVersion(version); setPreviewLoading(true);
    try {
      const data = await strategyApi.getVersion(id, version.id);
      if (request === previewRequest.current) setSelectedVersion(data);
    } catch (failure) { if (request === previewRequest.current) notify.error(getApiErrorMessage(failure)); }
    finally { if (request === previewRequest.current) setPreviewLoading(false); }
  };

  const fetchData = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    setError("");
    try {
      const [item, history] = await Promise.all([
        strategyApi.getById(id), strategyApi.getVersions(id, { page, page_size: pageSize }),
      ]);
      if (request !== generation.current) return;
      setStrategy(item);
      setVersions(history.results); setMetadata(history); accept(history);
    } catch (failure) {
      if (request === generation.current) setError(getApiErrorMessage(failure, "Could not load version history."));
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [id, page, pageSize, accept]);
  useEffect(() => { fetchData(); const guard = generation; return () => { guard.current++; }; }, [fetchData]);

  const handleRollback = async (versionId) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const confirmed = await customConfirm("Restore this saved version as the current strategy configuration? Running sessions keep their deployed version.", "Restore strategy version", "Restore version");
      if (!confirmed) return;
      await strategyApi.rollback(id, versionId);
      notify.success("Strategy version restored.");
      navigate(`/strategies/${id}/edit`);
    } catch (failure) {
      notify.error(getApiErrorMessage(failure, "Could not restore strategy version."));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const handleCreateVersion = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const notes = await customPrompt("Add change notes (optional). This snapshot captures the current saved configuration.", "", "Create snapshot", "Save snapshot");
      if (notes === null) return;
      await strategyApi.createVersion(id, notes);
      notify.success("Snapshot created.");
      await fetchData();
    } catch (failure) {
      notify.error(getApiErrorMessage(failure, "Could not create snapshot."));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [id, notify, fetchData]);

  const handleToggleAutoSave = useCallback(async (checked) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    const previous = strategy.auto_version_enabled;
    setStrategy((item) => ({ ...item, auto_version_enabled: checked }));
    try {
      await strategyApi.update(id, { auto_version_enabled: checked });
      notify.success(`Automatic snapshots ${checked ? "enabled" : "paused"}.`);
    } catch (failure) {
      setStrategy((item) => ({ ...item, auto_version_enabled: previous }));
      notify.error(getApiErrorMessage(failure, "Could not update snapshot settings."));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [id, strategy, notify]);

  // Workspace controls stay above the scrolling timeline, like the Studio toolbar.
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);
  useEffect(() => {
    setPageActions(<div className="page-toolbar flex items-center gap-3">
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        Auto snapshots
        <Switch checked={strategy?.auto_version_enabled ?? false}
          onCheckedChange={handleToggleAutoSave} disabled={loading || busy || !strategy || Boolean(error)}
          aria-label="Automatic version snapshots" />
      </label>
      <Button onClick={handleCreateVersion} disabled={loading || busy || !strategy || Boolean(error)}>
        <GitBranch />Snapshot
      </Button>
    </div>);
    return () => setPageActions(null);
  }, [strategy, loading, busy, error, handleCreateVersion, handleToggleAutoSave, setPageActions]);

  if (loading && !metadata.page) return <div className="flex h-64 items-center justify-center"><GlobalLoader text="Loading version history…" /></div>;
  if (error) return <div className="page-content"><p role="alert" className="text-destructive-text">{error}</p><Button className="justify-self-start" onClick={fetchData}>Retry</Button></div>;

  return <div className="scrollbar-theme min-h-0 flex-1 overflow-y-auto">
    <div className="page-content">
      {versions.length === 0 ? <div className="rounded-xl border border-border bg-card p-4 text-center">
        <History className="mx-auto mb-3 h-8 w-8 text-brand" aria-hidden="true" />
        <h2 className="font-semibold">No saved versions yet</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">Create a snapshot of your saved configuration, or turn on automatic snapshots to record future saves.</p>
        <Button className="mt-3" onClick={handleCreateVersion} disabled={busy}><GitBranch />Create first snapshot</Button>
      </div> : <ol aria-label="Strategy version history" className="space-y-3">
        {versions.map((version, index) => {
          const latest = page === 1 && index === 0;
          return <li key={version.id} className="relative pl-8">
            {/* Each segment ends at the next dot, including differently sized cards. */}
            {index < versions.length - 1 && <span aria-hidden="true" data-version-connector className="absolute -bottom-9 left-[7px] top-6 w-0.5 bg-input" />}
            <span aria-hidden="true" className={`absolute left-0 top-4 z-10 h-4 w-4 rounded-full border-2 ${latest ? "border-brand bg-brand" : "border-input bg-card"}`} />
            <article className="relative rounded-lg border border-border bg-card p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Button variant="plain" size="content" className="font-semibold" onClick={() => preview(version)} aria-label={`View version ${version.version_number}`}>
                      Version {version.version_number}
                    </Button>
                    {latest && <Badge variant="outline" className="border-brand/40 bg-brand/10 text-brand">Latest snapshot</Badge>}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                    <time dateTime={version.created_at}>{formatDateTime(version.created_at)}</time>
                    {version.created_by_username && <><span aria-hidden="true">·</span><span>{version.created_by_username}</span></>}
                  </div>
                  {version.change_notes && <p className="mt-2 whitespace-pre-wrap break-words text-sm text-muted-foreground">{version.change_notes}</p>}
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button variant="outline" size="icon" onClick={() => preview(version)} title={`View version ${version.version_number} details`}><Eye /></Button>
                  {!latest && <Button variant="warning" size="icon" onClick={() => handleRollback(version.id)} disabled={busy} title={`Restore version ${version.version_number}`}><RotateCcw /></Button>}
                </div>
              </div>
            </article>
          </li>;
        })}
      </ol>}

      <Pagination {...metadata} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Strategy version pages" />

      <Dialog open={Boolean(selectedVersion)} onOpenChange={(open) => { if (!open) { previewRequest.current++; setSelectedVersion(null); } }}>
        <DialogContent className="flex max-h-[90dvh] max-w-5xl flex-col overflow-hidden">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><GitBranch className="h-5 w-5 text-brand" />Version {selectedVersion?.version_number} details</DialogTitle></DialogHeader>
          {selectedVersion && <div className="scrollbar-theme min-h-0 flex-1 overflow-y-auto pr-2">
            {previewLoading ? <GlobalLoader inline text="Loading snapshot…" /> : <StrategySnapshotViewer snapshot={selectedVersion.config_snapshot} changes={selectedVersion.changes} previousVersionNumber={selectedVersion.previous_version_number} />}
          </div>}
        </DialogContent>
      </Dialog>
    </div>
  </div>;
}
