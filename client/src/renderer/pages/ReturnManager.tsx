import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { get, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TaxReturnRow {
  id: string;
  tax_year_id: string;
  year: number;
  entity_name: string;
  entity_type: string;
  entity_id: string;
  client_name: string;
  client_id: string;
  form_code: string;
  status: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "in_progress", label: "In Progress" },
  { value: "in_review", label: "In Review" },
  { value: "approved", label: "Approved" },
  { value: "filed", label: "Filed" },
];

const FORM_OPTIONS = [
  { value: "", label: "All Forms" },
  { value: "1120-S", label: "1120-S (S-Corp)" },
  { value: "1065", label: "1065 (Partnership)" },
  { value: "1120", label: "1120 (C-Corp)" },
];

const ENTITY_TYPE_LABELS: Record<string, string> = {
  scorp: "S-Corp",
  partnership: "Partnership",
  ccorp: "C-Corp",
  trust: "Trust",
  individual: "Individual",
};

type SortColumn = "client_name" | "entity_name" | "entity_type" | "year" | "form_code" | "status" | "created_at";
type SortDir = "asc" | "desc";

// ---------------------------------------------------------------------------
// Return Manager page
// ---------------------------------------------------------------------------

export default function ReturnManager() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [returns, setReturns] = useState<TaxReturnRow[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters — initialize from URL params (set by Returns menu shortcuts)
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [formFilter, setFormFilter] = useState(searchParams.get("form") || "");
  const [yearFilter, setYearFilter] = useState(searchParams.get("year") || "");

  // Sorting
  const [sortCol, setSortCol] = useState<SortColumn>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const firmName = user?.memberships?.[0]?.firm_name ?? "Your firm";

  // Sync filters when URL params change (e.g., user clicks a Returns menu shortcut)
  useEffect(() => {
    setFormFilter(searchParams.get("form") || "");
    setStatusFilter(searchParams.get("status") || "");
    setYearFilter(searchParams.get("year") || "");
  }, [searchParams]);

  // ---- Load data ----

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    const res = await get("/tax-returns/");
    if (res.ok) setReturns(res.data as TaxReturnRow[]);
    setLoading(false);
  }

  // ---- Delete ----

  async function handleDelete(id: string, entityName: string, year: number) {
    if (!confirm(`Delete the ${year} return for "${entityName}"? All field values will be permanently lost.`)) return;
    const res = await del(`/tax-returns/${id}/`);
    if (res.ok) {
      setReturns((prev) => prev.filter((r) => r.id !== id));
    } else {
      alert("Failed to delete return.");
    }
  }

  // ---- Filter + sort ----

  const availableYears = [...new Set(returns.map((r) => r.year))].sort((a, b) => b - a);

  const filtered = returns.filter((r) => {
    if (search) {
      const q = search.toLowerCase();
      if (
        !r.client_name.toLowerCase().includes(q) &&
        !r.entity_name.toLowerCase().includes(q) &&
        !r.form_code.toLowerCase().includes(q)
      ) return false;
    }
    if (statusFilter && r.status !== statusFilter) return false;
    if (formFilter && r.form_code !== formFilter) return false;
    if (yearFilter && r.year !== parseInt(yearFilter, 10)) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    switch (sortCol) {
      case "client_name": cmp = a.client_name.localeCompare(b.client_name); break;
      case "entity_name": cmp = a.entity_name.localeCompare(b.entity_name); break;
      case "entity_type": cmp = a.entity_type.localeCompare(b.entity_type); break;
      case "year": cmp = a.year - b.year; break;
      case "form_code": cmp = a.form_code.localeCompare(b.form_code); break;
      case "status": cmp = a.status.localeCompare(b.status); break;
      case "created_at": cmp = a.created_at.localeCompare(b.created_at); break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  function handleSort(col: SortColumn) {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  }

  function SortIndicator({ col }: { col: SortColumn }) {
    if (sortCol !== col) return <span className="ml-1 text-tx-muted/40">↕</span>;
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  // ---- Render ----

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Return Manager</h1>
          <p className="text-sm text-tx-secondary">
            {firmName} &mdash; {loading ? "Loading..." : `${filtered.length} returns`}
          </p>
        </div>
        <button
          onClick={loadData}
          className="rounded-lg bg-primary-subtle px-4 py-2 text-sm font-medium text-primary-text transition hover:bg-primary hover:text-white"
        >
          Refresh
        </button>
      </div>

      {/* Filter bar */}
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 shadow-sm">
        <input
          type="text"
          placeholder="Search client, entity, or form..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={formFilter}
          onChange={(e) => setFormFilter(e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          {FORM_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          <option value="">All Years</option>
          {availableYears.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        {(search || statusFilter || formFilter || yearFilter) && (
          <button
            onClick={() => { setSearch(""); setStatusFilter(""); setFormFilter(""); setYearFilter(""); }}
            className="text-xs text-primary-text hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-tx-secondary">Loading returns...</p>
      ) : sorted.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            {search || statusFilter || formFilter || yearFilter
              ? "No returns match your filters."
              : "No returns yet. Create a return from the Entity detail page."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <table className="min-w-full divide-y divide-border zebra-table">
            <thead className="bg-surface-alt">
              <tr>
                <SortableHeader col="client_name" label="Client" onSort={handleSort} indicator={<SortIndicator col="client_name" />} />
                <SortableHeader col="entity_name" label="Entity" onSort={handleSort} indicator={<SortIndicator col="entity_name" />} />
                <SortableHeader col="entity_type" label="Type" onSort={handleSort} indicator={<SortIndicator col="entity_type" />} />
                <SortableHeader col="year" label="Tax Year" onSort={handleSort} indicator={<SortIndicator col="year" />} />
                <SortableHeader col="form_code" label="Form" onSort={handleSort} indicator={<SortIndicator col="form_code" />} />
                <SortableHeader col="status" label="Status" onSort={handleSort} indicator={<SortIndicator col="status" />} />
                <SortableHeader col="created_at" label="Created" onSort={handleSort} indicator={<SortIndicator col="created_at" />} />
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {sorted.map((r) => (
                <tr key={r.id} className="transition hover:bg-primary-subtle">
                  <td className="px-4 py-3">
                    <Link to={`/clients/${r.client_id}`} className="text-sm font-medium text-primary-text hover:underline">
                      {r.client_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/clients/${r.client_id}/entities/${r.entity_id}`} className="text-sm font-medium text-primary-text hover:underline">
                      {r.entity_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">
                      {ENTITY_TYPE_LABELS[r.entity_type] || r.entity_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm tabular-nums text-tx">{r.year}</td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium text-tx">{r.form_code}</span>
                  </td>
                  <td className="px-4 py-3">
                    <ReturnStatusPill status={r.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">
                    {new Date(r.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/tax-returns/${r.id}/editor`}
                        className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white transition hover:bg-primary-hover"
                      >
                        Open
                      </Link>
                      <button
                        onClick={() => handleDelete(r.id, r.entity_name, r.year)}
                        className="rounded-md px-2.5 py-1.5 text-xs font-medium text-danger transition hover:bg-danger-subtle"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-border bg-surface-alt px-4 py-2">
            <span className="text-xs text-tx-muted">
              Showing {sorted.length} of {returns.length} returns
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SortableHeader({
  col,
  label,
  onSort,
  indicator,
}: {
  col: SortColumn;
  label: string;
  onSort: (col: SortColumn) => void;
  indicator: React.ReactNode;
}) {
  return (
    <th
      onClick={() => onSort(col)}
      className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary transition hover:text-tx"
    >
      {label}
      {indicator}
    </th>
  );
}

function ReturnStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-surface-alt text-tx-secondary",
    in_progress: "bg-amber-50 text-amber-700",
    in_review: "bg-amber-50 text-amber-700",
    approved: "bg-primary-subtle text-primary-text",
    filed: "bg-card text-success",
  };
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] || colors.draft
      }`}
    >
      {status.replace("_", " ")}
    </span>
  );
}
