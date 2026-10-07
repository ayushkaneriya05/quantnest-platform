import { useCallback, useEffect, useRef, useState } from "react";
import { ensureFreshAccessToken, getWebSocketUrl } from "@/shared/services/api";
import { researchApi } from "@/shared/services/researchApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { isResearchActive, mergeResearchRuns } from "./researchState";

export { isResearchActive } from "./researchState";

export function useResearchData(session) {
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
    for (const run of accepted) latestRecords.current.set(run.id, { ...latestRecords.current.get(run.id), ...run });
    if (visible) setRuns((previous) => mergeResearchRuns(previous, accepted, full));
    if (updateActive && accepted.length) {
      activeRevision.current += 1;
      setActiveRun((current) => {
        const active = accepted.find(isResearchActive);
        return active || (accepted.some((run) => run.id === current?.id) ? null : current);
      });
    }
  }, []);
  const reload = useCallback(async (quiet = false, page = 1) => {
    const current = generation.current;
    const activeVersion = activeRevision.current;
    try {
      const [response, active] = await Promise.all([researchApi.runs(session, { page }), researchApi.runs(null, { active: true })]);
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
      socket.onopen = () => { setConnected(true); attempts = 0; reloadRef.current(true); };
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
  }, [receive]);

  useEffect(() => {
    if (!activeRun) return;
    const timer = setInterval(() => reloadRef.current(true), 10000);
    return () => clearInterval(timer);
  }, [activeRun]);
  return { runs, receive, loading, connected, reload, activeRun, active: Boolean(activeRun),
           hasMore: Boolean(nextPage), loadMore: () => reload(false, nextPage) };
}
