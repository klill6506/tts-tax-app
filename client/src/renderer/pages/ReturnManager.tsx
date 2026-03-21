import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { get, del, post } from "../lib/api";

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
  preparer_name: string;
  fein: string;
  extension_filed: boolean;
  created_at: string;
  updated_at: string;
}

interface PaginatedResponse {
  count: number;
  results: TaxReturnRow[];
  counts: Record<string, number>;
  next: string | null;
  previous: string | null;
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

const ENTITY_TABS = [
  { value: "", label: "All" },
  { value: "scorp", label: "S-Corp" },
  { value: "partnership", label: "Partnership" },
  { value: "ccorp", label: "C-Corp" },
  { value: "trust", label: "Trust" },
  { value: "individual", label: "Individual" },
] as const;

const ENTITY_TYPE_LABELS: Record<string, string> = {
  scorp: "S-Corp",
  partnership: "Partnership",
  ccorp: "C-Corp",
  trust: "Trust",
  individual: "Individual",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-surface-alt text-tx-secondary",
  in_progress: "bg-blue-50 text-blue-700",
  in_review: "bg-amber-50 text-amber-700",
  approved: "bg-orange-50 text-orange-700",
  filed: "bg-emerald-50 text-emerald-700",
};

type SortColumn = "client_name" | "entity_name" | "status" | "updated_at";

const PAGE_SIZE = 25;

// ---------------------------------------------------------------------------
// Return Manager page
// ---------------------------------------------------------------------------

export default function ReturnManager() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Read filters from URL
  const entityType = searchParams.get("entity_type") || "";
  const statusFilter = searchParams.get("status") || "";
  const yearFilter = searchParams.get("year") || "";
  const searchQuery = searchParams.get("search") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);
  const ordering = searchParams.get("ordering") || "-updated_at";

  // Local search input (debounced before writing to URL)
  const [searchInput, setSearchInput] = useState(searchQuery);

  // Data
  const [data, setData] = useState<PaginatedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [preparers, setPreparers] = useState<{ id: string; name: string }[]>([]);
  const [years, setYears] = useState<number[]>([]);

  // New client form
  const [showNewClient, setShowNewClient] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [creating, setCreating] = useState(false);

  const firmName = user?.memberships?.[0]?.firm_name ?? "Your firm";

  // --- URL param helpers ---

  const setParam = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        // Reset to page 1 when any filter changes
        if (key !== "page") next.delete("page");
        return next;
      });
    },
    [setSearchParams]
  );

  // --- Debounced search ---

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (searchInput !== searchQuery) {
        setParam("search", searchInput);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput, searchQuery, setParam]);

  // Sync input when URL changes externally
  useEffect(() => {
    setSearchInput(searchParams.get("search") || "");
  }, [searchParams]);

  // --- Load preparers and years once ---

  useEffect(() => {
    get("/preparers/").then((res) => {
      if (res.ok) {
        setPreparers(res.data as { id: string; name: string }[]);
      }
    });
    // Get available years from a quick request (no pagination, just counts)
    get("/tax-returns/?page_size=1").then((res) => {
      // We'll derive years from entity data; for now use current year ± 1
      const currentYear = new Date().getFullYear();
      setYears([currentYear, currentYear - 1, currentYear - 2]);
    });
  }, []);

  // --- Load returns (fires on any filter/page change) ---

  useEffect(() => {
    loadData();
  }, [entityType, statusFilter, yearFilter, searchQuery, page, ordering]);

  async function loadData() {
    setLoading(true);
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    if (statusFilter) params.set("status", statusFilter);
    if (yearFilter) params.set("year", yearFilter);
    if (searchQuery) params.set("search", searchQuery);
    if (page > 1) params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));
    if (ordering) params.set("ordering", ordering);

    const qs = params.toString();
    const res = await get(`/tax-returns/?${qs}`);
    if (res.ok) {
      setData(res.data as PaginatedResponse);
    }
    setLoading(false);
  }

  // --- Sort ---

  function handleSort(col: SortColumn) {
    const currentCol = ordering.replace("-", "");
    if (currentCol === col) {
      setParam("ordering", ordering.startsWith("-") ? col : `-${col}`);
    } else {
      setParam("ordering", col);
    }
  }

  function SortIndicator({ col }: { col: SortColumn }) {
    const currentCol = ordering.replace("-", "");
    if (currentCol !== col) return <span className="ml-1 text-tx-muted/40">↕</span>;
    return <span className="ml-1">{ordering.startsWith("-") ? "↓" : "↑"}</span>;
  }

  // --- New client ---

  async function handleCreateClient(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newClientName.trim();
    if (!trimmed) return;
    setCreating(true);
    const res = await post("/clients/", { name: trimmed });
    setCreating(false);
    if (res.ok) {
      setNewClientName("");
      setShowNewClient(false);
      navigate(`/clients/${(res.data as { id: string }).id}`);
    } else {
      alert("Failed to create client.");
    }
  }

  // --- Delete ---

  async function handleDelete(id: string, entityName: string, year: number) {
    if (!confirm(`Delete the ${year} return for "${entityName}"? All field values will be permanently lost.`))
      return;
    const res = await del(`/tax-returns/${id}/`);
    if (res.ok) loadData();
    else alert("Failed to delete return.");
  }

  // --- Pagination ---

  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const startIdx = (page - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(page * PAGE_SIZE, totalCount);
  const returns = data?.results ?? [];
  const counts = data?.counts ?? {};

  // --- Relative time formatting ---

  function relativeTime(iso: string): string {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  // --- Active filters check ---

  const hasFilters = !!(entityType || statusFilter || yearFilter || searchQuery);

  // --- Render ---

  return (
    <div>
      {/* Header row: search + actions */}
      <div className="mb-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search clients, entities, or FEIN..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full rounded-lg border border-input-border bg-input pl-9 pr-8 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
          />
          <svg className="absolute left-3 top-2.5 h-4 w-4 text-tx-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {searchInput && (
            <button
              onClick={() => { setSearchInput(""); setParam("search", ""); }}
              className="absolute right-2 top-2 rounded p-0.5 text-tx-muted hover:text-tx"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={() => setShowNewClient(true)}
            className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover"
          >
            + New Client
          </button>
        </div>
      </div>

      {/* New client form */}
      {showNewClient && (
        <form onSubmit={handleCreateClient} className="mb-4 flex items-center gap-2 rounded-lg border border-border-subtle bg-card p-3">
          <input
            autoFocus
            type="text"
            placeholder="Client name..."
            value={newClientName}
            onChange={(e) => setNewClientName(e.target.value)}
            className="w-full max-w-sm rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
          />
          <button type="submit" disabled={creating || !newClientName.trim()} className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50">
            {creating ? "Creating..." : "Create"}
          </button>
          <button type="button" onClick={() => { setShowNewClient(false); setNewClientName(""); }} className="rounded-lg px-3 py-2 text-sm font-medium text-tx-secondary transition hover:bg-surface-alt">
            Cancel
          </button>
        </form>
      )}

      {/* Entity type tabs */}
      <div className="mb-4 flex items-center gap-1 border-b border-border">
        {ENTITY_TABS.map((tab) => {
          const isActive = entityType === tab.value;
          const count = tab.value ? counts[tab.value] ?? 0 : counts["all"] ?? totalCount;
          return (
            <button
              key={tab.value}
              onClick={() => setParam("entity_type", tab.value)}
              className={`relative px-4 py-2.5 text-sm font-medium transition ${
                isActive
                  ? "text-primary-text"
                  : "text-tx-secondary hover:text-tx"
              }`}
            >
              {tab.label}
              {count > 0 && (
                <span className={`ml-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs ${
                  isActive ? "bg-primary-subtle text-primary-text" : "bg-surface-alt text-tx-muted"
                }`}>
                  {count}
                </span>
              )}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
              )}
            </button>
          );
        })}
      </div>

      {/* Filter row */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setParam("status", e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={searchParams.get("preparer") || ""}
          onChange={(e) => setParam("preparer", e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          <option value="">All Preparers</option>
          {preparers.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          value={yearFilter}
          onChange={(e) => setParam("year", e.target.value)}
          className="rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        >
          <option value="">All Years</option>
          {years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        {hasFilters && (
          <button
            onClick={() => setSearchParams({})}
            className="text-xs text-primary-text hover:underline"
          >
            Clear all filters
          </button>
        )}
        <span className="ml-auto text-xs text-tx-muted">
          {firmName}
        </span>
      </div>

      {/* Table */}
      {loading && !data ? (
        <p className="text-sm text-tx-secondary">Loading returns...</p>
      ) : returns.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            {hasFilters
              ? "No returns found. Try adjusting your filters."
              : "No returns yet. Click + New Client to get started."}
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-surface-alt">
                <tr>
                  <SortableHeader col="client_name" label="Client" onSort={handleSort} indicator={<SortIndicator col="client_name" />} />
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">FEIN</th>
                  <SortableHeader col="status" label="Status" onSort={handleSort} indicator={<SortIndicator col="status" />} />
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Preparer</th>
                  <SortableHeader col="updated_at" label="Modified" onSort={handleSort} indicator={<SortIndicator col="updated_at" />} />
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {returns.map((r) => (
                  <tr key={r.id} className="transition hover:bg-primary-subtle">
                    <td className="px-4 py-3">
                      <Link to={`/tax-returns/${r.id}/editor`} className="text-sm font-medium text-primary-text hover:underline">
                        {r.client_name}
                      </Link>
                      <div className="text-xs text-tx-muted">{r.entity_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">
                        {ENTITY_TYPE_LABELS[r.entity_type] || r.entity_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm tabular-nums text-tx-secondary">{r.fein || "—"}</td>
                    <td className="px-4 py-3">
                      <ReturnStatusPill status={r.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-tx-secondary">{r.preparer_name || "—"}</td>
                    <td className="px-4 py-3 text-sm text-tx-secondary" title={new Date(r.updated_at).toLocaleString()}>
                      {relativeTime(r.updated_at)}
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

            {/* Pagination footer */}
            <div className="flex items-center justify-between border-t border-border bg-surface-alt px-4 py-2.5">
              <span className="text-xs text-tx-muted">
                Showing {startIdx}–{endIdx} of {totalCount} returns
              </span>
              {totalPages > 1 && (
                <div className="flex items-center gap-1">
                  <button
                    disabled={page <= 1}
                    onClick={() => setParam("page", String(page - 1))}
                    className="rounded px-2 py-1 text-xs font-medium text-tx-secondary transition hover:bg-card disabled:opacity-40"
                  >
                    ← Prev
                  </button>
                  {pageNumbers(page, totalPages).map((p, i) =>
                    p === "..." ? (
                      <span key={`dot-${i}`} className="px-1 text-xs text-tx-muted">…</span>
                    ) : (
                      <button
                        key={p}
                        onClick={() => setParam("page", String(p))}
                        className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                          p === page
                            ? "bg-primary text-white"
                            : "text-tx-secondary hover:bg-card"
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setParam("page", String(page + 1))}
                    className="rounded px-2 py-1 text-xs font-medium text-tx-secondary transition hover:bg-card disabled:opacity-40"
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pagination helper
// ---------------------------------------------------------------------------

function pageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | "...")[] = [1];
  if (current > 3) pages.push("...");
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
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
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        STATUS_COLORS[status] || STATUS_COLORS.draft
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
