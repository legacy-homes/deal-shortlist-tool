import { useState, useCallback } from "react";
import type { SavedSearch, PipelineDeal } from "../types";

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
