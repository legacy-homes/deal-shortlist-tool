import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Loader2 } from "lucide-react";
import { Button } from "../components/Button";
import { Table } from "../components/Table";
import { Badge } from "../components/Badge";
import { Card, CardHeader, CardContent } from "../components/Card";
import { getComparables } from "../api/dealfinderApi";
import type { ComparableProperty } from "../types";

export function ComparablesPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const postcode = searchParams.get("postcode") ?? "";
  const type = searchParams.get("type") ?? "";
  const beds = Number(searchParams.get("beds") ?? 0);
  const tenure = (searchParams.get("tenure") ?? "FREEHOLD") as
    | "FREEHOLD"
    | "LEASEHOLD"
    | "ANY";

  // Default all comparables as qualified (checked)
  const [qualified, setQualified] = useState<Set<number>>(new Set());

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["comparables", postcode, type, beds, tenure],
    queryFn: () => getComparables(postcode, type, beds, tenure),
    enabled: !!postcode,
    staleTime: 5 * 60 * 1000,
  });

  // When data loads (including instantly from cache), default all rows to qualified
  useEffect(() => {
    if (data) {
      setQualified(new Set((data.properties ?? []).map((_, i) => i)));
    }
  }, [data]);

  function toggleQualified(idx: number) {
    setQualified((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  const columns = [
    {
      header: "Comparable Address",
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
      cell: () => (
        <span className="text-gray-400 text-xs italic">—</span>
      ),
    },
    {
      header: "Qualify Comparable",
      cell: (_row: ComparableProperty) => {
        const idx = data?.properties?.indexOf(_row) ?? -1;
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
            {type} · {beds} bed · {postcode} · {tenure.charAt(0) + tenure.slice(1).toLowerCase()}
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
              <div className="flex items-center gap-4">
                <span className="font-semibold text-gray-800">Median Price</span>
                {data.median_price != null ? (
                  <Badge variant="blue">£{data.median_price.toLocaleString()}</Badge>
                ) : (
                  <Badge variant="gray">Not enough data</Badge>
                )}
                {data.property_count != null && (
                  <span className="text-sm text-gray-500">
                    from {data.property_count} comparable{data.property_count !== 1 ? "s" : ""}
                  </span>
                )}
                {data.search_params != null && (
                  <span className="text-sm text-gray-400">· {data.search_params.label}</span>
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
