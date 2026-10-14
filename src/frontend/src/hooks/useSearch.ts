import { useCallback, useRef, useState } from 'react';
import { apiClient, ApiError, type EntityType, type SearchFilter, type SearchMode, type SearchResponse, type SearchResultItem } from '../api/client';
import { fieldValue } from '../utils/format';

export interface SearchArgs {
  entity: EntityType;
  mode: SearchMode;
  text: string;
  libraries?: string[];
  filters: SearchFilter[];
  pageSize: number;
}

export function useSearch() {
  const abortRef = useRef<AbortController | undefined>(undefined);
  const [response, setResponse] = useState<SearchResponse | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [hasSearched, setHasSearched] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);

  const clear = useCallback(() => { setResponse(undefined); setError(undefined); setAuthRequired(false); }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = undefined;
    setLoading(false);
    setError(undefined);
  }, []);

  const run = useCallback(async (args: SearchArgs) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(undefined);
    setAuthRequired(false);
    setHasSearched(true);
    try {
      const serverFilters = args.filters.filter((filter) => !(filter.op === 'not_contains' && (filter.key === 'title' || filter.key === 'author')));
      const result = await apiClient.search({
        entity: args.entity,
        mode: args.mode,
        text: args.mode === 'number' ? args.text.replace(/^#/, '') : args.text,
        libraries: args.libraries,
        filters: serverFilters,
        page: 1,
        page_size: args.pageSize
      }, controller.signal);
      const localNegative = args.filters.filter((filter) => filter.op === 'not_contains' && (filter.key === 'title' || filter.key === 'author'));
      const filtered = localNegative.length ? applyClientNegation(result.results, localNegative) : result.results;
      setResponse({ ...result, total: localNegative.length ? filtered.length : result.total, results: filtered });
      return result;
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return undefined;
      setResponse(undefined);
      if (err instanceof ApiError && (err.status === 401 || err.code === 'authorization_required')) {
        setAuthRequired(true);
      } else {
        setError(err instanceof ApiError ? err.friendlyMessage() : 'Search failed.');
      }
      return undefined;
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = undefined;
        setLoading(false);
      }
    }
  }, []);

  return { response, loading, error, hasSearched, authRequired, run, clear, cancel };
}

function applyClientNegation(items: SearchResultItem[], filters: SearchFilter[]) {
  return items.filter((item) => filters.every((filter) => {
    const needles = filter.value.split('|').map((value) => value.trim().toLowerCase()).filter(Boolean);
    const haystack = fieldValue(item, filter.key).toLowerCase();
    return needles.every((needle) => {
      const options = needle.startsWith('@') ? [needle, needle.slice(1)] : [needle];
      return options.every((option) => !haystack.includes(option));
    });
  }));
}

