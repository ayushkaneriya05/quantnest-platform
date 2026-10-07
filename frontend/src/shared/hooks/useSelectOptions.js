import { useEffect, useState } from "react";
import api from "@/shared/services/api";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export function useSelectOptions(resource, filters, open, search, page, selectedValue) {
  const [state, setState] = useState({ results: [], has_more: false, loading: false, error: "" });
  const [selected, setSelected] = useState(null);
  const filterKey = JSON.stringify(filters || {});
  const requestKey = JSON.stringify([resource, filterKey, search, page]);

  useEffect(() => {
    if (!resource || !open) return;
    const controller = new AbortController();
    setState({ results: [], has_more: false, loading: true, error: "" });
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get("/common/choices/", {
          params: { ...JSON.parse(filterKey), resource, search, page }, signal: controller.signal,
        });
        if (!controller.signal.aborted) setState({ ...data, key: requestKey, loading: false, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setState({ key: requestKey, results: [], has_more: false, loading: false,
          error: getApiErrorMessage(error, "Could not load options") });
      }
    }, search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [resource, filterKey, open, search, page, requestKey]);

  useEffect(() => {
    setSelected(null);
    if (!resource || !/^\d+$/.test(selectedValue || "")) return;
    const controller = new AbortController();
    api.get("/common/choices/", {
      params: { ...JSON.parse(filterKey), resource, id: selectedValue }, signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setSelected(data.results[0] || null);
    }).catch(() => { /* List requests show failures; a missing selection remains unselected. */ });
    return () => controller.abort();
  }, [resource, filterKey, selectedValue]);

  const current = resource && open && state.key !== requestKey ?
    { results: [], has_more: false, loading: true, error: "" } : state;
  return { ...current, selected };
}
