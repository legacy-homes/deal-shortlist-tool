import { useNavigate } from "react-router-dom";
import { PlusCircle, Trash2, ExternalLink } from "lucide-react";
import { Button } from "../components/Button";
import { Table } from "../components/Table";
import { Badge } from "../components/Badge";
import { useSavedSearches } from "../store/storage";
import type { SavedSearch } from "../types";

export function HomePage() {
  const navigate = useNavigate();
  const { searches, removeSearch } = useSavedSearches();

  const columns = [
    {
      header: "Search Area Label",
      cell: (row: SavedSearch) => (
        <span className="font-medium text-gray-900">{row.label}</span>
      ),
    },
    {
      header: "Searched Date",
      cell: (row: SavedSearch) =>
        new Date(row.searchedAt).toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        }),
    },
    {
      header: "Deals Found",
      cell: (row: SavedSearch) => (
        <Badge variant={row.results.deals_found > 0 ? "green" : "gray"}>
          {row.results.deals_found} deal{row.results.deals_found !== 1 ? "s" : ""}
        </Badge>
      ),
    },
    {
      header: "Link to Search",
      cell: (row: SavedSearch) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => navigate(`/search/${row.id}`)}
          className="gap-1"
        >
          <ExternalLink size={14} />
          View
        </Button>
      ),
    },
    {
      header: "",
      cell: (row: SavedSearch) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            if (confirm(`Delete "${row.label}"?`)) removeSearch(row.id);
          }}
          className="text-red-500 hover:text-red-700 hover:bg-red-50"
        >
          <Trash2 size={14} />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Saved Searches</h1>
          <p className="text-sm text-gray-500 mt-1">
            Pick an existing search to review, or create a new one.
          </p>
        </div>
        <Button onClick={() => navigate("/search/new")} size="lg">
          <PlusCircle size={18} />
          Create New Search
        </Button>
      </div>

      {/* Table */}
      <Table
        columns={columns}
        data={searches}
        emptyMessage="No saved searches yet. Click 'Create New Search' to get started."
      />
    </div>
  );
}
