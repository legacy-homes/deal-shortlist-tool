import { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Loader2 } from "lucide-react";
import { Button } from "../components/Button";
import { Table } from "../components/Table";
import { Badge } from "../components/Badge";
import { Card, CardHeader, CardContent } from "../components/Card";
import { getComparables } from "../api/dealfinderApi";
import {
  comparableCacheKey,
  saveComparable,
  loadComparable,
  calcMedian,
} from "../store/storage";
import type { ComparableProperty, ComparablesCacheEntry } from "../types";

export function ComparablesPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const postcode = searchParams.get("postcode") ?? "";
  const type = searchParams.get("type") ?? "";
  const beds = Number(searchParams.get("beds") ?? 0);
  const tenure = (searchParams.get("tenure") ?? "FREEHOLD") as
    | "FREEHOLD"
    | "LEASEHOLD"
    | "ANY";

  const cacheKey = useMemo(
    () => comparableCacheKey(postcode, type, beds, tenure),
    [postcode, type, beds, tenure]
  );

  // ── Initialize qualified set synchronously from localStorage ──────────────
  // Since SearchPage always pre-seeds localStorage before navigating here,
  // this initializer will find cached data and restore saved qualification state.
  const [qualified, setQualified] = useState<Set<number>>(() => {
    const cached = loadComparable(cacheKey);
    const props = cached?.properties ?? [];
    if (!props.length) return new Set<number>(); // fallback: useEffect will handle
    if (cached?.qualifiedIds == null) {
      return new Set(props.map((_, i) => i)); // all qualified by default
    }
    // Restore saved: convert IDs back to current indices
    return new Set(
      props
        .map((p, i) => (cached.qualifiedIds!.includes(p.id) ? i : -1))
        .filter((i) => i !== -1)
    );
  });

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["comparables", postcode, type, beds, tenure],
    queryFn: () => getComparables(postcode, type, beds, tenure),
    enabled: !!postcode,
    staleTime: 5 * 60 * 1000,
  });

  // Fallback init from useQuery data when localStorage had nothing
  const initializedRef = useRef(false);
  useEffect(() => {
    if (data && !initializedRef.current) {
      initializedRef.current = true;
      const props = data.properties ?? [];
      if (qualified.size === 0 && props.length > 0) {
        const cached = loadComparable(cacheKey);
        if (cached?.qualifiedIds == null) {
          setQualified(new Set(props.map((_, i) => i)));
        } else {
          setQualified(
            new Set(
              props
                .map((p, i) => (cached.qualifiedIds!.includes(p.id) ? i : -1))
                .filter((i) => i !== -1)
            )
          );
        }
      }
    }
  }, [data, cacheKey, qualified.size]);

  // ── Live median recalculated from qualified rows ───────────────────────────
  const effectiveMedian = useMemo(() => {
    const props = data?.properties ?? [];
    const prices = [...qualified]
      .map((i) => props[i]?.sold_price)
      .filter((p): p is number => typeof p === "number");
    // Fall back to original API median during init or if nothing qualified
    return prices.length > 0 ? calcMedian(prices) : (data?.median_price ?? null);
  }, [qualified, data]);

  // ── Toggle a comparable's qualification and persist immediately ───────────
  function toggleQualified(idx: number) {
    setQualified((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);

      const props = data?.properties ?? [];

      // Build qualified IDs and recalculate median
      const qualifiedIds = [...next]
        .map((i) => props[i]?.id)
        .filter((id): id is string => !!id);
      const qualifiedPrices = [...next]
        .map((i) => props[i]?.sold_price)
        .filter((p): p is number => typeof p === "number");
      const newMedian = calcMedian(qualifiedPrices);

      // Build updated cache entry, preserving all API fields
      const existing = loadComparable(cacheKey);
      const updated: ComparablesCacheEntry = {
        status: existing?.status ?? "success",
        median_price: existing?.median_price ?? data?.median_price ?? null,
        property_count: existing?.property_count ?? data?.property_count ?? null,
        search_params: existing?.search_params ?? data?.search_params ?? null,
        properties: existing?.properties ?? data?.properties ?? null,
        qualifiedIds,
        qualifiedMedian: newMedian,
      };

      // Persist to localStorage and TQ cache simultaneously
      saveComparable(cacheKey, updated);
      queryClient.setQueryData(
        ["comparables", postcode, type, beds, tenure],
        updated
      );

      return next;
    });
  }

  const totalCount = data?.properties?.length ?? 0;
  const qualifiedCount = qualified.size;
  const isAdjusted = qualifiedCount < totalCount;

  const columns = [
    {
      header: "Comparable Address",
      className: "min-w-[220px]",
      cell: (row: ComparableProperty) => (
        <span className="font-medium text-gray-900 text-xs">{row.address}</span>
      ),
    },
    {
      header: "Rightmove Link",
      cell: (row: ComparableProperty) => (
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
      header: "Sold Price",
      cell: (row: ComparableProperty) => (
        <span className="font-semibold">£{row.sold_price.toLocaleString()}</span>
      ),
    },
    {
      header: "Sold Date",
      cell: (row: ComparableProperty) => (
        <span className="text-xs">{row.sold_date}</span>
      ),
    },
    {
      header: "Property Type",
      cell: (row: ComparableProperty) => (
        <span className="text-xs">{row.property_type}</span>
      ),
    },
    {
      header: "Bedrooms",
      cell: (row: ComparableProperty) => row.bedrooms,
    },
    {
      header: "Floor Area",
      cell: () => <span className="text-gray-400 text-xs italic">—</span>,
    },
    {
      header: "Qualify Comparable",
      cell: (_row: ComparableProperty) => {
        const idx = (data as ComparablesCacheEntry | undefined)?.properties?.indexOf(_row) ?? -1;
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
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Comparable Sales</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {type} · {beds} bed · {postcode} ·{" "}
            {tenure.charAt(0) + tenure.slice(1).toLowerCase()}
          </p>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 size={20} className="animate-spin" />
          Loading comparable sales…
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm">
          {(error as Error).message}
        </div>
      )}

      {/* Results */}
      {data && (
        <div className="space-y-3">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-semibold text-gray-800">Effective Median Price</span>
                {effectiveMedian != null ? (
                  <Badge variant="blue">£{effectiveMedian.toLocaleString()}</Badge>
                ) : (
                  <Badge variant="gray">Not enough data</Badge>
                )}
                {isAdjusted && (
                  <Badge variant="gray">
                    {qualifiedCount} of {totalCount} qualified
                  </Badge>
                )}
                {!isAdjusted && totalCount > 0 && (
                  <span className="text-sm text-gray-500">
                    {totalCount} comparable{totalCount !== 1 ? "s" : ""}
                  </span>
                )}
                {data.search_params != null && (
                  <span className="text-sm text-gray-400">· {data.search_params.label}</span>
                )}
                {isAdjusted && data.median_price != null && (
                  <span className="text-sm text-gray-400">
                    (original: £{data.median_price.toLocaleString()})
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <Table
                columns={columns}
                data={data.properties ?? []}
                emptyMessage="No comparable sales found."
              />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
