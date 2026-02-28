import { useState, useCallback } from "react";
import type { SavedSearch, PipelineDeal, GetMedianPropertiesResponse } from "../types";

const SAVED_SEARCHES_KEY = "dealfinder_saved_searches";
const PIPELINE_KEY = "dealfinder_pipeline";

// ─── Saved Searches ───────────────────────────────────────────────────────────

function loadSavedSearches(): SavedSearch[] {
  try {
    const raw = localStorage.getItem(SAVED_SEARCHES_KEY);
    return raw ? (JSON.parse(raw) as SavedSearch[]) : [];
  } catch {
    return [];
  }
}

function persistSavedSearches(searches: SavedSearch[]) {
  localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(searches));
}

export function useSavedSearches() {
  const [searches, setSearches] = useState<SavedSearch[]>(loadSavedSearches);

  const addSearch = useCallback((search: SavedSearch) => {
    setSearches((prev) => {
      const updated = [search, ...prev];
      persistSavedSearches(updated);
      return updated;
    });
  }, []);

  const removeSearch = useCallback((id: string) => {
    setSearches((prev) => {
      const updated = prev.filter((s) => s.id !== id);
      persistSavedSearches(updated);
      return updated;
    });
  }, []);

  const getSearch = useCallback(
    (id: string) => searches.find((s) => s.id === id),
    [searches]
  );

  return { searches, addSearch, removeSearch, getSearch };
}

// ─── Pipeline Deals ───────────────────────────────────────────────────────────

function loadPipelineDeals(): PipelineDeal[] {
  try {
    const raw = localStorage.getItem(PIPELINE_KEY);
    return raw ? (JSON.parse(raw) as PipelineDeal[]) : [];
  } catch {
    return [];
  }
}

function persistPipelineDeals(deals: PipelineDeal[]) {
  localStorage.setItem(PIPELINE_KEY, JSON.stringify(deals));
}

export function usePipelineDeals() {
  const [deals, setDeals] = useState<PipelineDeal[]>(loadPipelineDeals);

  const addDeal = useCallback((deal: PipelineDeal) => {
    setDeals((prev) => {
      const updated = [deal, ...prev];
      persistPipelineDeals(updated);
      return updated;
    });
  }, []);

  const removeDeal = useCallback((id: string) => {
    setDeals((prev) => {
      const updated = prev.filter((d) => d.id !== id);
      persistPipelineDeals(updated);
      return updated;
    });
  }, []);

  return { deals, addDeal, removeDeal };
}

// ─── Simple UUID helper ───────────────────────────────────────────────────────
export function newId(): string {
  return crypto.randomUUID();
}

// ─── Comparables Cache ────────────────────────────────────────────────────────
// Keyed by "postcode|type|beds|tenure" — shared across all saved searches.

const COMPARABLES_CACHE_KEY = "dealfinder_comparables_cache";

type ComparablesStore = Record<string, GetMedianPropertiesResponse>;

function loadComparablesStore(): ComparablesStore {
  try {
    const raw = localStorage.getItem(COMPARABLES_CACHE_KEY);
    return raw ? (JSON.parse(raw) as ComparablesStore) : {};
  } catch {
    return {};
  }
}

export function comparableCacheKey(
  postcode: string,
  type: string,
  beds: number,
  tenure: string
): string {
  return `${postcode}|${type}|${beds}|${tenure}`;
}

export function saveComparable(
  key: string,
  data: GetMedianPropertiesResponse
): void {
  const store = loadComparablesStore();
  store[key] = data;
  localStorage.setItem(COMPARABLES_CACHE_KEY, JSON.stringify(store));
}

export function loadComparable(
  key: string
): GetMedianPropertiesResponse | undefined {
  return loadComparablesStore()[key];
}

export function loadAllComparables(): ComparablesStore {
  return loadComparablesStore();
}
