import { usePagination } from "@/shared/hooks/usePagination";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { format, isValid, parseISO, subDays } from "date-fns";
import { Terminal, FlaskConical, Radio } from "lucide-react";
import { executionReportsApi } from "@/shared/services/executionReportsApi";
import { journalApi } from "@/shared/services/journalApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import { usePlatform } from "@/shared/context/platform";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { subscribeTerminalUpdates } from "@/shared/hooks/useWebSocket";

export const modes = [
  { value: "TERMINAL", label: "Terminal", icon: Terminal, description: "Manual simulated execution · net of recorded charges" },
  { value: "PAPER", label: "Paper", icon: FlaskConical, description: "Strategy simulation · net of recorded charges" },
  { value: "LIVE", label: "Live", icon: Radio, description: "Broker execution · before fees" },
];
export const reviewModes = (scopes) => modes.filter(({ value }) => value === 'TERMINAL' || scopes.includes(value.toLowerCase()));
export const displayMoney = (value) => value == null ? "N/A" : formatCurrency(value);
export const displayNumber = (value) => value == null ? "N/A" : formatNumber(value);
export const pnlTone = (value) => Number(value) < 0 ? "text-rose-700 dark:text-rose-400" : Number(value) > 0 ? "text-emerald-700 dark:text-emerald-400" : "text-foreground";

export function useReviewWorkspace(kind) {
  const { executionScopes, loading: platformLoading } = usePlatform();
  const sources = useMemo(() => reviewModes(executionScopes), [executionScopes]);
  const [params, setParams] = useSearchParams();
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ loading: true, error: "", details: null, trades: null });
  const defaults = useMemo(() => ({ date_from: format(subDays(new Date(), 29), "yyyy-MM-dd"), date_to: format(new Date(), "yyyy-MM-dd") }), []);
  const query = params.toString();
  const filters = useMemo(() => {
    const values = Object.fromEntries(new URLSearchParams(query));
    const source = sources.some(({ value }) => value === values.source) ? values.source : "TERMINAL";
    const result = { ...defaults, source };
    for (const field of ["date_from", "date_to"]) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(values[field] || "") && isValid(parseISO(values[field]))) result[field] = values[field];
    }
    // A link to an unavailable source must not carry its account or strategy filters.
    if (!values.source || values.source === source) {
      for (const field of ["account_id", "strategy_id", "instrument_id"]) {
        if ((field !== "strategy_id" || source !== "TERMINAL") && /^[1-9]\d*$/.test(values[field] || "")) result[field] = values[field];
      }
      if (values.search) result.search = values.search.slice(0, 100);
      if (kind === "journal") {
        if (["all", "reviewed", "unreviewed"].includes(values.reviewed)) result.reviewed = values.reviewed;
      }
    }
    return result;
  }, [query, defaults, kind, sources]);
  const key = JSON.stringify(filters);
  // Quotes update valuation locally. Only ledger changes reload report inputs
  // so new positions subscribe and closed positions stop contributing to P&L.
  const refreshTimer = useRef(null);
  const onLedgerUpdate = useCallback((event) => {
    if (!["POSITION_UPDATE", "ACCOUNT_UPDATE", "TRADE_UPDATE", "RECONNECTED"].includes(event?.event_type)) return;
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => setRefreshKey(value => value + 1), 200);
  }, []);
  usePaperTradingWebSocket({ enabled: kind === "report" && filters.source === "PAPER" });
  const paperUpdate = usePaperTradingUpdate();
  const previousPaperUpdate = useRef(paperUpdate);
  useEffect(() => {
    if (paperUpdate !== previousPaperUpdate.current && kind === "report" && filters.source === "PAPER") onLedgerUpdate(paperUpdate);
    previousPaperUpdate.current = paperUpdate;
  }, [paperUpdate, kind, filters.source, onLedgerUpdate]);
  useLiveTradingWebSocket(onLedgerUpdate, { enabled: kind === "report" && filters.source === "LIVE" });
  useEffect(() => {
    if (kind === "report" && filters.source === "TERMINAL") return subscribeTerminalUpdates(onLedgerUpdate);
    return undefined;
  }, [kind, filters.source, onLedgerUpdate]);
  useEffect(() => () => clearTimeout(refreshTimer.current), [key]);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(key);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(kind === "journal");
  useEffect(() => {
    const controller = new AbortController();
    setSummaryLoading(true);
    setState(previous => ({ ...previous, details: null, error: "" }));
    if (platformLoading) return () => controller.abort();
    const timer = setTimeout(async () => {
      try {
        const details = kind === "journal" ? await journalApi.summary(JSON.parse(key), controller.signal) : await executionReportsApi.report(JSON.parse(key), controller.signal);
        if (!controller.signal.aborted) setState(previous => ({ ...previous, details: details.data }));
      } catch (error) { if (!controller.signal.aborted) setState(previous => ({ ...previous, error: getApiErrorMessage(error) })); }
      finally { if (!controller.signal.aborted) setSummaryLoading(false); }
    }, filters.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, kind, refreshKey, filters.search, platformLoading]);
  useEffect(() => { setState(previous => ({ ...previous, trades: null })); }, [key]);
  useEffect(() => {
    if (kind !== "journal" || platformLoading) return undefined;
    const controller = new AbortController(); setTableLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await executionReportsApi.trades({ ...JSON.parse(key), page, page_size: pageSize }, controller.signal);
        if (!controller.signal.aborted) { setState(previous => ({ ...previous, trades: response.data, error: "" })); accept(response.data); }
      } catch (error) { if (!controller.signal.aborted) setState(previous => ({ ...previous, error: getApiErrorMessage(error) })); }
      finally { if (!controller.signal.aborted) setTableLoading(false); }
    }, filters.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, kind, page, pageSize, accept, refreshKey, filters.search, platformLoading]);
  const update = useCallback((changes) => {
    const next = { ...filters, ...changes, page: 1, page_size: pageSize };
    if (changes.source && changes.source !== filters.source) {
      delete next.account_id; delete next.strategy_id; delete next.instrument_id; delete next.search; delete next.reviewed;
    }
    setParams(Object.fromEntries(Object.entries(next).filter(([, value]) => value !== "" && value != null)));
  }, [filters, pageSize, setParams]);
  const turnPage = setPage;
  const reload = useCallback(() => setRefreshKey((value) => value + 1), []);
  return { ...state, loading: summaryLoading || tableLoading, filters: { ...filters, page, page_size: pageSize }, update, turnPage, setPageSize, reload };
}
