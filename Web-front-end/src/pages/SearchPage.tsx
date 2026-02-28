import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueries } from "@tanstack/react-query";
import { Search, Save, ExternalLink, ArrowRightCircle, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Select } from "../components/Select";
import { Table } from "../components/Table";
import { Badge } from "../components/Badge";
import { Dialog } from "../components/Dialog";
import { Card, CardHeader, CardContent } from "../components/Card";
import { findDeals, getComparables } from "../api/dealfinderApi";
import { useSavedSearches, usePipelineDeals, newId } from "../store/storage";
import type { FindDealsParams, DealProperty } from "../types";

const DEFAULT_PARAMS: FindDealsParams = {
  rightmove_url: "",
  price_difference_threshold: 50000,
  max_properties: 10,
  include_featured: false,
  tenure: "FREEHOLD",
  min_properties_for_median: 5,
};

export function SearchPage() {
  const { id } = useParams<{ id: string }>();
  const isNew = id === "new";
  const navigate = useNavigate();

  const { addSearch, getSearch } = useSavedSearches();
  const { addDeal } = usePipelineDeals();

  // ── Form state ──────────────────────────────────────────────────────────────
  const [params, setParams] = useState<FindDealsParams>(DEFAULT_PARAMS);
  const [qualified, setQualified] = useState<Set<number>>(new Set());
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState("");

  // Load saved search when viewing an existing one
  useEffect(() => {
    if (!isNew && id) {
      const saved = getSearch(id);
      if (saved) setParams(saved.params);
    }
  }, [id, isNew, getSearch]);

  // Determine results to show (existing saved search or fresh mutation result)
  const savedSearch = !isNew && id ? getSearch(id) : undefined;

  // ── API call ─────────────────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: findDeals,
    onSuccess: (data) => {
      // Auto-qualify all deals by default
      const defaultQualified = new Set(
        data.deals.map((_, i) => i)
      );
      setQualified(defaultQualified);
    },
  });

  const results = mutation.data ?? savedSearch?.results;
  const deals = results?.deals ?? [];

  // ── Background-prefetch comparables for every deal ────────────────────────
  // Uses the same query keys as ComparablesPage so the cache is shared.
  // By the time the user clicks "View", data is already there.
  const comparableQueries = useQueries({
    queries: deals.map((deal) => ({
      queryKey: ["comparables", deal.postcode, deal.property_type, deal.bedrooms, params.tenure],
      queryFn: () =>
        getComparables(deal.postcode, deal.property_type, deal.bedrooms, params.tenure),
      staleTime: 5 * 60 * 1000,
      enabled: deals.length > 0,
    })),
  });

  // Map "postcode|type|beds" → query state for use in the table column
  const comparableStatus = new Map(
    deals.map((deal, i) => [
      `${deal.postcode}|${deal.property_type}|${deal.bedrooms}`,
      comparableQueries[i],
    ])
  );

  // ── Handlers ─────────────────────────────────────────────────────────────────
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate(params);
  }

  function toggleQualified(idx: number) {
    setQualified((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function handleSave() {
    if (!mutation.data || !saveName.trim()) return;
    addSearch({
      id: newId(),
      label: saveName.trim(),
      searchedAt: new Date().toISOString(),
      params,
      results: mutation.data,
    });
    setSaveDialogOpen(false);
    setSaveName("");
    navigate("/");
  }

  function handleSendToNextStage(deal: DealProperty, idx: number) {
    addDeal({
      id: newId(),
      savedSearchId: id ?? "unsaved",
      savedSearchLabel: (savedSearch?.label ?? saveName) || "Unsaved Search",
      sentAt: new Date().toISOString(),
      property: deal,
    });
    // Unqualify after sending
    setQualified((prev) => {
      const next = new Set(prev);
      next.delete(idx);
      return next;
    });
    navigate("/pipeline");
  }

  // ── Columns ──────────────────────────────────────────────────────────────────
  const columns = [
    {
      header: "Address",
      className: "min-w-[260px]",
      cell: (row: DealProperty) => (
        <span className="font-medium text-gray-900 text-xs">{row.address}</span>
      ),
    },
    {
      header: "Postcode",
      cell: (row: DealProperty) => <span className="text-xs">{row.postcode}</span>,
    },
    {
      header: "Type",
      cell: (row: DealProperty) => <span className="text-xs">{row.property_type}</span>,
    },
    {
      header: "Beds",
      cell: (row: DealProperty) => row.bedrooms,
    },
    {
      header: "Asking Price",
      cell: (row: DealProperty) => (
        <span className="font-semibold">£{row.asking_price.toLocaleString()}</span>
      ),
    },
    {
      header: "Median Price",
      cell: (row: DealProperty) => `£${row.median_price.toLocaleString()}`,
    },
    {
      header: "Difference",
      cell: (row: DealProperty) => (
        <Badge variant="green">£{row.difference.toLocaleString()} below</Badge>
      ),
    },
    {
      header: "Sample Size",
      cell: (row: DealProperty) => row.sample_size,
    },
    {
      header: "Rightmove Link",
      cell: (row: DealProperty) => (
        <a
          href={row.link}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-blue-600 hover:underline text-xs"
        >
          <ExternalLink size={12} />
          View
        </a>
      ),
    },
    {
      header: "Comparables",
      cell: (row: DealProperty) => {
        const key = `${row.postcode}|${row.property_type}|${row.bedrooms}`;
        const q = comparableStatus.get(key);
        const isFetching = q?.isFetching ?? false;
        const isReady = q?.isSuccess ?? false;
        return (
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              navigate(
                `/comparables?postcode=${encodeURIComponent(row.postcode)}&type=${encodeURIComponent(row.property_type)}&beds=${row.bedrooms}&tenure=${params.tenure}`
              )
            }
            className="text-xs gap-1"
          >
            {isFetching ? (
              <Loader2 size={12} className="animate-spin text-gray-400" />
            ) : isReady ? (
              <CheckCircle2 size={12} className="text-green-500" />
            ) : (
              <ExternalLink size={12} />
            )}
            View
          </Button>
        );
      },
    },
    {
      header: "Qualified",
      cell: (row: DealProperty) => {
        const idx = deals.indexOf(row);
        return (
          <input
            type="checkbox"
            checked={qualified.has(idx)}
            onChange={() => toggleQualified(idx)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 cursor-pointer"
          />
        );
      },
    },
    {
      header: "Send to Next Stage",
      cell: (row: DealProperty) => {
        const idx = deals.indexOf(row);
        return (
          <Button
            size="sm"
            variant="primary"
            disabled={!qualified.has(idx)}
            onClick={() => handleSendToNextStage(row, idx)}
            className="text-xs whitespace-nowrap"
          >
            <ArrowRightCircle size={14} />
            Send
          </Button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          {isNew ? "New Search" : savedSearch?.label ?? "Search"}
        </h1>
        {mutation.data && (
          <Button variant="secondary" onClick={() => setSaveDialogOpen(true)}>
            <Save size={16} />
            Save Search
          </Button>
        )}
      </div>

      {/* Input form */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-800">Search Parameters</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              id="url"
              label="Rightmove URL"
              placeholder="https://www.rightmove.co.uk/property-for-sale/find.html?..."
              value={params.rightmove_url}
              onChange={(e) => setParams({ ...params, rightmove_url: e.target.value })}
              required
              className="w-full"
            />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Input
                id="threshold"
                label="Price Diff Threshold (£)"
                type="number"
                value={params.price_difference_threshold}
                onChange={(e) =>
                  setParams({ ...params, price_difference_threshold: Number(e.target.value) })
                }
              />
              <Input
                id="max_props"
                label="Max Properties"
                type="number"
                value={params.max_properties}
                onChange={(e) =>
                  setParams({ ...params, max_properties: Number(e.target.value) })
                }
              />
              <Input
                id="min_median"
                label="Min Comparables"
                type="number"
                value={params.min_properties_for_median}
                onChange={(e) =>
                  setParams({ ...params, min_properties_for_median: Number(e.target.value) })
                }
              />
              <Select
                id="tenure"
                label="Tenure"
                value={params.tenure}
                onChange={(e) =>
                  setParams({ ...params, tenure: e.target.value as FindDealsParams["tenure"] })
                }
                options={[
                  { value: "FREEHOLD", label: "Freehold" },
                  { value: "LEASEHOLD", label: "Leasehold" },
                  { value: "ANY", label: "Any" },
                ]}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="featured"
                type="checkbox"
                checked={params.include_featured}
                onChange={(e) => setParams({ ...params, include_featured: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <label htmlFor="featured" className="text-sm text-gray-700">
                Include featured listings
              </label>
            </div>
            <Button
              type="submit"
              size="lg"
              disabled={mutation.isPending}
              className="w-full md:w-auto"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Finding deals… (this may take 1–3 min)
                </>
              ) : (
                <>
                  <Search size={18} />
                  Shortlist Deals
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error */}
      {mutation.isError && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm">
          {(mutation.error as Error).message}
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">Shortlisted Deals</h2>
            <Badge variant={deals.length > 0 ? "green" : "gray"}>
              {deals.length} deal{deals.length !== 1 ? "s" : ""} found
            </Badge>
            <span className="text-sm text-gray-500">
              from {results.total_processed} properties processed
            </span>
          </div>
          <Table
            columns={columns}
            data={deals}
            emptyMessage="No deals found matching your threshold. Try lowering the price difference threshold."
          />
        </div>
      )}

      {/* Save dialog */}
      <Dialog
        open={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        title="Save Search"
      >
        <div className="space-y-4">
          <Input
            id="search-name"
            label="Search Name"
            placeholder="e.g. Manchester Semi-Detached Feb 2026"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!saveName.trim()}>
              <Save size={16} />
              Save
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
