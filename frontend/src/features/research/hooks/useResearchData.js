import { useCallback, useEffect, useRef, useState } from "react";
import { ensureFreshAccessToken, getWebSocketUrl } from "@/shared/services/api";
import { researchApi } from "@/shared/services/researchApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";


export const isResearchActive = (run) => ["PENDING", "RUNNING"].includes(run?.status);

export function mergeResearchRuns(previous, incoming, full = true) {
  const records = new Map(previous.map((run) => [run.id, run]));
  for (const run of incoming) {
    const current = records.get(run.id);
    if (current && current.revision > run.revision) continue;
    records.set(run.id, { ...current, ...run, ...(full ? { loadedRevision: run.revision } : {}) });
  }
  return [...records.values()].sort((a, b) => a.id - b.id);
}


export function useResearchData(session) {
  const [allowance, setAllowance] = useState(null);
  const allowanceRequest = useRef(0);
  const refreshAllowance = useCallback(async () => {
    const revision = ++allowanceRequest.current;
    try { const response = await researchApi.allowance(); if (revision === allowanceRequest.current) setAllowance(response.data); }
    catch { /* Existing balance stays visible; admission remains authoritative. */ }
  }, []);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [nextPage, setNextPage] = useState(null);
  const { notify } = useNotifications();
  const generation = useRef(0);
  const activeRevision = useRef(0);
  const latestRecords = useRef(new Map());
  const loadedPage = useRef(1);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const receive = useCallback((records, full = true, updateActive = true, visible = true) => {
    const accepted = records.filter((run) => !latestRecords.current.has(run.id) || latestRecords.current.get(run.id).revision <= run.revision);
    if (accepted.some((run) => !isResearchActive(run) && isResearchActive(latestRecords.current.get(run.id)))) refreshAllowance();
    for (const run of accepted) latestRecords.current.set(run.id, { ...latestRecords.current.get(run.id), ...run });
    if (visible) setRuns((previous) => mergeResearchRuns(previous, accepted, full));
    if (updateActive && accepted.length) {
      activeRevision.current += 1;
      setActiveRun((current) => {
        const active = accepted.find(isResearchActive);
        return active || (accepted.some((run) => run.id === current?.id) ? null : current);
      });
    }
  }, [refreshAllowance]);
  const reload = useCallback(async (quiet = false, page = 1) => {
    const current = generation.current;
    const activeVersion = activeRevision.current;
    try {
      const [response, active] = await Promise.all([
        session ? researchApi.runs(session, { page }) : { data: { results: [], next: null } },
        researchApi.runs(null, { active: true }),
      ]);
      if (current !== generation.current) return;
      receive(response.data.results, true, false);
      receive(active.data.results, true, false, false);
      if (activeVersion === activeRevision.current) {
        const record = active.data.results[0];
        const newest = record && latestRecords.current.get(record.id);
        const resolved = newest && newest.revision > record.revision ? newest : record;
        setActiveRun(isResearchActive(resolved) ? resolved : null);
      }
      if (page >= loadedPage.current) {
        loadedPage.current = page;
        setNextPage(response.data.next ? page + 1 : null);
      }
    } catch (error) {
      if (current === generation.current && !quiet) notify.error(getApiErrorMessage(error, "Could not load research"));
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [notify, session, receive]);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    generation.current += 1;
    setLoading(true);
    setRuns([]);
    setNextPage(null);
    loadedPage.current = 1;
    reload();
    return () => { generation.current += 1; };
  }, [reload]);

  useEffect(() => {
    let socket, timer, disposed = false, attempts = 0;
    async function connect() {
      try { await ensureFreshAccessToken(); } catch { return; }
      if (disposed) return;
      socket = new WebSocket(getWebSocketUrl("/ws/research/"));
      socket.onopen = () => { setConnected(true); attempts = 0; reloadRef.current(true); refreshAllowance(); };
      socket.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type !== "research.update") return;
          const run = message.run;
          receive([run], false, true, !sessionRef.current || String(run.session) === String(sessionRef.current));
          if (sessionRef.current && String(run.session) !== String(sessionRef.current)) return;
          // New turns can arrive through progress before their POST response.
          if (!isResearchActive(run) || !latestRecords.current.get(run.id)?.request) {
            const response = await researchApi.run(run.id);
            if (!disposed) receive([response.data], true, true,
              !sessionRef.current || String(response.data.session) === String(sessionRef.current));
          }
        } catch { /* Polling and reconnect retrieve the persisted revision. */ }
      };
      socket.onclose = (event) => {
        setConnected(false);
        if (!disposed && event.code !== 4401) timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 30000));
      };
    }
    connect();
    return () => { disposed = true; clearTimeout(timer); socket?.close(); };
  }, [receive, refreshAllowance]);

  useEffect(() => {
    if (!activeRun) return;
    let disposed = false;
    const timer = setInterval(async () => {
      try {
        const { data } = await researchApi.run(activeRun.id);
        if (!disposed) receive([data], true, true, !sessionRef.current || String(data.session) === String(sessionRef.current));
      } catch { /* WebSocket/reconnect can recover the saved revision. */ }
    }, 10000);
    return () => { disposed = true; clearInterval(timer); };
  }, [activeRun?.id, receive]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refreshAllowance();
    window.addEventListener("focus", refreshAllowance);
    return () => window.removeEventListener("focus", refreshAllowance);
  }, [refreshAllowance]);
  useEffect(() => {
    if (!allowance?.period_end) return;
    const delay = new Date(allowance.period_end).getTime() - Date.now();
    const timer = setTimeout(refreshAllowance, Math.min(Math.max(1000, delay + 1000), 2147483647));
    return () => clearTimeout(timer);
  }, [allowance, refreshAllowance]);
  return { allowance, refreshAllowance, runs, receive, loading, connected, reload, activeRun, active: Boolean(activeRun),
           hasMore: Boolean(nextPage), loadMore: () => reload(false, nextPage) };
}
