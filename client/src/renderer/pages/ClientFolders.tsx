import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { get } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FolderRow {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  ein: string;
  client_id: string;
  client_name: string;
  document_count: number;
  last_upload: string | null;
  total_size: number;
}

interface PaginatedFolderResponse {
  count: number;
  results: FolderRow[];
  counts: Record<string, number>;
  next: string | null;
  previous: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

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

type SortColumn = "name" | "document_count" | "last_upload";

const PAGE_SIZE = 25;

// ---------------------------------------------------------------------------
// Client Folders page
// ---------------------------------------------------------------------------

export default function ClientFolders() {
  const [searchParams, setSearchParams] = useSearchParams();

  const entityType = searchParams.get("entity_type") || "";
  const searchQuery = searchParams.get("search") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);
  const ordering = searchParams.get("ordering") || "name";

  const [searchInput, setSearchInput] = useState(searchQuery);
  const [data, setData] = useState<PaginatedFolderResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // --- URL param helpers ---

  const setParam = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
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

  useEffect(() => {
    setSearchInput(searchParams.get("search") || "");
  }, [searchParams]);

  // --- Load folder data ---

  useEffect(() => {
    loadData();
  }, [entityType, searchQuery, page, ordering]);

  async function loadData() {
    setLoading(true);
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    if (searchQuery) params.set("search", searchQuery);
    if (page > 1) params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));
    if (ordering) params.set("ordering", ordering);

    const res = await get(`/documents/folders/?${params.toString()}`);
    if (res.ok) {
      setData(res.data as PaginatedFolderResponse);
    }
    setLoading(false);
  }

  // --- Sort ---

  function handleSort(col: SortColumn) {
    const currentCol = ordering.replace("-", "");
    if (currentCol === col) {
      setParam("ordering", ordering.startsWith("-") ? col : `-${col}`);
    } else {
      setParam("ordering", `-${col}`);
    }
  }

  function SortIndicator({ col }: { col: SortColumn }) {
    const currentCol = ordering.replace("-", "");
    if (currentCol !== col) return <span className="ml-1 text-tx-muted/40">↕</span>;
    return <span className="ml-1">{ordering.startsWith("-") ? "↓" : "↑"}</span>;
  }

  // --- Pagination ---

  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const startIdx = (page - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(page * PAGE_SIZE, totalCount);
  const folders = data?.results ?? [];
  const counts = data?.counts ?? {};

  const hasFilters = !!(entityType || searchQuery);

  // --- Helpers ---

  function relativeTime(iso: string | null): string {
    if (!iso) return "—";
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

  function formatSize(bytes: number): string {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // --- Render ---

  return (
    <div>
      {/* Header row: search */}
      <div className="mb-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search entities, clients, or FEIN..."
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
      </div>

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
                isActive ? "text-primary-text" : "text-tx-secondary hover:text-tx"
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
              {isActive && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
            </button>
          );
        })}
      </div>

      {/* Filter row */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {hasFilters && (
          <button
            onClick={() => setSearchParams({})}
            className="text-xs text-primary-text hover:underline"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Table */}
      {loading && !data ? (
        <p className="text-sm text-tx-secondary">Loading folders...</p>
      ) : folders.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            {hasFilters
              ? "No folders found. Try adjusting your filters."
              : "No entities yet."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-surface-alt">
              <tr>
                <th
                  onClick={() => handleSort("name")}
                  className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary transition hover:text-tx"
                >
                  Entity Name
                  <SortIndicator col="name" />
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Client</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">FEIN</th>
                <th
                  onClick={() => handleSort("document_count")}
                  className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary transition hover:text-tx"
                >
                  Documents
                  <SortIndicator col="document_count" />
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Size</th>
                <th
                  onClick={() => handleSort("last_upload")}
                  className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary transition hover:text-tx"
                >
                  Last Upload
                  <SortIndicator col="last_upload" />
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {folders.map((f) => (
                <tr key={f.entity_id} className="transition hover:bg-primary-subtle">
                  <td className="px-4 py-3">
                    <Link to={`/folders/${f.entity_id}`} className="text-sm font-medium text-primary-text hover:underline">
                      {f.entity_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">{f.client_name}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">
                      {ENTITY_TYPE_LABELS[f.entity_type] || f.entity_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm tabular-nums text-tx-secondary">{f.ein || "—"}</td>
                  <td className="px-4 py-3">
                    {f.document_count > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-primary-subtle px-2 py-0.5 text-xs font-medium text-primary-text">
                        {f.document_count}
                      </span>
                    ) : (
                      <span className="text-sm text-tx-muted">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-tx-secondary">{formatSize(f.total_size)}</td>
                  <td className="px-4 py-3 text-sm text-tx-secondary" title={f.last_upload ? new Date(f.last_upload).toLocaleString() : ""}>
                    {relativeTime(f.last_upload)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/folders/${f.entity_id}`}
                      className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white transition hover:bg-primary-hover"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination footer */}
          <div className="flex items-center justify-between border-t border-border bg-surface-alt px-4 py-2.5">
            <span className="text-xs text-tx-muted">
              Showing {startIdx}–{endIdx} of {totalCount} folders
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
                        p === page ? "bg-primary text-white" : "text-tx-secondary hover:bg-card"
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
