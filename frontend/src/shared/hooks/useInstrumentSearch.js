import { useEffect, useState } from "react";
import { instrumentsApi } from "@/shared/services/instrumentsApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export function useInstrumentSearch(query, filters, open, search = instrumentsApi.search) {
  const [state, setState] = useState({ results: [], loading: false, error: "" });
  const filterKey = JSON.stringify(filters || {});
  const requestKey = JSON.stringify([query, filterKey]);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setState({ results: [], loading: true, error: "" });
    const timer = setTimeout(async () => {
      try {
        const results = await search({ ...JSON.parse(filterKey), q: query.trim() }, { signal: controller.signal });
        if (!controller.signal.aborted) setState({ key: requestKey, results, loading: false, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setState({ key: requestKey, results: [], loading: false,
          error: getApiErrorMessage(error, "Could not search instruments") });
      }
    }, query ? 300 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, filterKey, requestKey, open, search]);
  if (!open) return { results: [], loading: false, error: "" };
  return state.key === requestKey ? state : { results: [], loading: true, error: "" };
}
