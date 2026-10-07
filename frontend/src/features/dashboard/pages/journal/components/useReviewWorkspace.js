import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { format, subDays } from "date-fns";
import { Terminal, FlaskConical, Radio } from "lucide-react";
import { executionReportsApi } from "@/shared/services/executionReportsApi";
import { journalApi } from "@/shared/services/journalApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";

export const modes = [
  { value: "TERMINAL", label: "Terminal", icon: Terminal, description: "Manual simulated execution · before fees" },
  { value: "PAPER", label: "Paper", icon: FlaskConical, description: "Strategy simulation · net of recorded charges" },
  { value: "LIVE", label: "Live", icon: Radio, description: "Broker execution · before fees" },
];
export const displayMoney = (value) => value == null ? "N/A" : formatCurrency(value);
export const displayNumber = (value) => value == null ? "N/A" : formatNumber(value);
export const pnlTone = (value) => Number(value) < 0 ? "text-rose-400" : Number(value) > 0 ? "text-emerald-400" : "text-slate-200";

export function useReviewWorkspace(kind) {
  const [params, setParams] = useSearchParams();
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ loading: true, error: "", details: null, trades: null });
  const defaults = useMemo(() => ({ date_from: format(subDays(new Date(), 29), "yyyy-MM-dd"), date_to: format(new Date(), "yyyy-MM-dd") }), []);
  const query = params.toString();
  const filters = useMemo(() => {
    const values = Object.fromEntries(new URLSearchParams(query));
    if (kind === "report") { delete values.reviewed; delete values.page; }
    return { ...defaults, ...values, source: modes.some((mode) => mode.value === values.source) ? values.source : "TERMINAL" };
  }, [query, defaults, kind]);
  const key = JSON.stringify(filters);
  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true, error: "", details: null, trades: null });
    const timer = setTimeout(async () => {
      try {
        const [details, trades] = await Promise.all([
          kind === "journal" ? journalApi.summary(JSON.parse(key), controller.signal) : executionReportsApi.report(JSON.parse(key), controller.signal),
          ...(kind === "journal" ? [executionReportsApi.trades(JSON.parse(key), controller.signal)] : []),
        ]);
        if (!controller.signal.aborted) setState({ loading: false, error: "", details: details.data, trades: trades?.data ?? null });
      } catch (error) {
        if (!controller.signal.aborted) setState({ loading: false, error: getApiErrorMessage(error, "Could not load execution records"), details: null, trades: null });
      }
    }, filters.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, kind, refreshKey, filters.search]);
  const update = useCallback((changes) => {
    const next = { ...filters, ...changes, page: 1 };
    if (changes.source && changes.source !== filters.source) {
      delete next.account_id; delete next.strategy_id; delete next.instrument_id; delete next.search; delete next.reviewed;
    }
    setParams(Object.fromEntries(Object.entries(next).filter(([, value]) => value !== "" && value != null)));
  }, [filters, setParams]);
  const turnPage = (page) => setParams({ ...filters, page: String(page) });
  const reload = useCallback(() => setRefreshKey((value) => value + 1), []);
  return { ...state, filters, update, turnPage, reload };
}
