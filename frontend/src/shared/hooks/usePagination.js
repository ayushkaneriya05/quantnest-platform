import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigationType, useSearchParams } from "react-router-dom";
import { useEnums } from "@/shared/context/EnumsContext";
import { formatDateInput } from "@/shared/utils/formatters";

// Domain hooks own fetching. This hook only owns URL page state and filter resets.
export function usePagination(filterKey = "", namespace = "") {
  const { enums } = useEnums();
  const defaults = enums.PaginationDefaults;
  const [search, setSearch] = useSearchParams();
  const navigation = useNavigationType();
  const pageKey = namespace ? `${namespace}_page` : "page";
  const sizeKey = namespace ? `${namespace}_page_size` : "page_size";
  const previousFilter = useRef(filterKey);
  const changed = previousFilter.current !== filterKey;
  const reset = changed && navigation !== 'POP';
  const pageText = search.get(pageKey) || "";
  const rawPage = /^\d+$/.test(pageText) ? Number(pageText) : NaN;
  const rawSize = Number(search.get(sizeKey));
  const pageSize = defaults?.page_sizes.includes(rawSize) ? rawSize : defaults?.page_size;
  const page = reset || !Number.isSafeInteger(rawPage) || rawPage < 1 ? 1 : rawPage;
  const update = useCallback((nextPage, nextSize, replace = false) => {
    setSearch(current => {
      const next = new URLSearchParams(current);
      next.set(pageKey, String(nextPage));
      if (nextSize) next.set(sizeKey, String(nextSize));
      return next;
    }, { replace });
  }, [pageKey, sizeKey, setSearch]);
  useEffect(() => {
    if (changed) {
      previousFilter.current = filterKey;
      if (reset && rawPage !== 1) update(1, pageSize, true);
    }
  }, [changed, reset, rawPage, filterKey, pageSize, update]);
  const setPage = useCallback(value => {
    if (value !== page) update(value, pageSize);
  }, [page, pageSize, update]);
  const setPageSize = useCallback(value => update(1, value), [update]);
  const accept = useCallback(meta => {
    if (meta.page !== page || (search.has(pageKey) && search.get(pageKey) !== String(meta.page))
      || (search.has(sizeKey) && search.get(sizeKey) !== String(meta.page_size))) update(meta.page, meta.page_size, true);
  }, [page, search, pageKey, sizeKey, update]);
  const resetFilters = useCallback(keys => setSearch(current => {
    const next = new URLSearchParams(current);
    keys.forEach(key => next.delete(namespace ? `${namespace}_${key}` : key));
    next.set(pageKey, '1');
    return next;
  }), [namespace, pageKey, setSearch]);
  return { page, pageSize, setPage, setPageSize, accept, resetFilters, ready: !!defaults };
}

// String filters live beside the page in the URL, so reload and browser history
// restore the same dataset. Changing a filter resets its list atomically.
export function useQueryState(key, initial = "", { namespace = "", resetPage = true, replace = false } = {}) {
  const [params, setParams] = useSearchParams();
  const queryKey = namespace ? `${namespace}_${key}` : key;
  const value = params.get(queryKey) ?? initial;
  const update = useCallback(nextValue => {
    setParams(current => {
      const next = new URLSearchParams(current);
      if (nextValue === initial || nextValue === "") next.delete(queryKey);
      else next.set(queryKey, nextValue);
      if (resetPage) next.set(namespace ? `${namespace}_page` : "page", "1");
      return next;
    }, { replace });
  }, [setParams, queryKey, namespace, resetPage, replace, initial]);
  return [value, update];
}

export function useQueryDateState(key, namespace = "") {
  const [text, update] = useQueryState(key, "", { namespace });
  const date = useMemo(() => /^\d{4}-\d{2}-\d{2}$/.test(text) ? new Date(`${text}T00:00:00`) : null, [text]);
  const setDate = useCallback(value => update(formatDateInput(value)), [update]);
  return [date && Number.isFinite(date.getTime()) ? date : null, setDate];
}
