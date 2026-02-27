import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientRow {
  id: string;
  name: string;
  status: string;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ClientRow[];
}

// ---------------------------------------------------------------------------
// Client Manager — the home page
// ---------------------------------------------------------------------------

const PAGE_SIZE = 50;

export default function Dashboard() {
  const { user } = useAuth();
  const [clients, setClients] = useState<ClientRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // New client form
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const firmName = user?.memberships?.[0]?.firm_name ?? "Your firm";

  // Fetch clients (paginated + server-side search)
  const fetchClients = useCallback(
    async (pageNum: number, query: string) => {
      setLoading(true);
      const params = new URLSearchParams({
        page: String(pageNum),
        page_size: String(PAGE_SIZE),
        ordering: "name",
      });
      if (query.trim()) params.set("search", query.trim());

      const res = await get(`/clients/?${params}`);
      if (res.ok) {
        const data = res.data as PaginatedResponse;
        setClients(data.results);
        setTotalCount(data.count);
      }
      setLoading(false);
    },
    []
  );

  // Load on mount and when page/search changes
  useEffect(() => {
    fetchClients(page, search);
  }, [page, search, fetchClients]);

  // Debounced search — wait 300ms after typing stops
  function handleSearchInput(value: string) {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      setSearch(value);
    }, 300);
  }

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    setCreating(true);
    const res = await post("/clients/", { name: trimmed });
    setCreating(false);
    if (res.ok) {
      setNewName("");
      setShowNew(false);
      fetchClients(page, search);
    } else {
      alert("Failed to create client.");
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete "${name}" and ALL entities, tax years, and returns?`)) return;
    const res = await del(`/clients/${id}/`);
    if (res.ok) {
      const newTotal = totalCount - 1;
      const newTotalPages = Math.ceil(newTotal / PAGE_SIZE);
      const targetPage = page > newTotalPages ? Math.max(1, newTotalPages) : page;
      setPage(targetPage);
      fetchClients(targetPage, search);
    } else {
      alert("Failed to delete client.");
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Client Manager</h1>
          <p className="text-sm text-tx-secondary">
            {firmName} &mdash; {loading ? "Loading..." : `${totalCount} clients`}
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover"
        >
          + New Client
        </button>
      </div>

      {/* New client form */}
      {showNew && (
        <form onSubmit={handleCreate} className="mb-4 flex items-center gap-2 rounded-lg border border-border-subtle bg-card p-3">
          <input
            autoFocus
            type="text"
            placeholder="Client name (individual)..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full max-w-sm rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
          />
          <button type="submit" disabled={creating || !newName.trim()} className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50">
            {creating ? "Creating..." : "Create"}
          </button>
          <button type="button" onClick={() => { setShowNew(false); setNewName(""); }} className="rounded-lg px-3 py-2 text-sm font-medium text-tx-secondary transition hover:bg-surface-alt">
            Cancel
          </button>
        </form>
      )}

      {/* Search */}
      <div className="mb-4 flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 shadow-sm">
        <input
          type="text"
          placeholder="Search clients..."
          value={searchInput}
          onChange={(e) => handleSearchInput(e.target.value)}
          className="w-64 rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        />
        {searchInput && (
          <button
            onClick={() => { setSearchInput(""); setSearch(""); setPage(1); }}
            className="text-xs text-primary-text hover:underline"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-tx-secondary">Loading clients...</p>
      ) : clients.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            {search ? "No clients match your search." : "No clients yet. Click '+ New Client' to get started."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <table className="min-w-full divide-y divide-border zebra-table">
            <thead className="bg-surface-alt">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Client</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {clients.map((r) => (
                <tr key={r.id} className="transition hover:bg-primary-subtle">
                  <td className="px-4 py-3">
                    <Link to={`/clients/${r.id}`} className="text-sm font-semibold text-primary-text hover:underline">
                      {r.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${r.status === "active" ? "bg-primary-subtle text-primary-text" : "bg-surface-alt text-tx-secondary"}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link to={`/clients/${r.id}`} className="rounded-md bg-primary-subtle px-2.5 py-1 text-xs font-medium text-primary-text transition hover:bg-primary hover:text-white">Open</Link>
                      <button onClick={() => handleDelete(r.id, r.name)} className="rounded-md px-2.5 py-1 text-xs font-medium text-danger transition hover:bg-danger-subtle">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination footer */}
          <div className="flex items-center justify-between border-t border-border bg-surface-alt px-4 py-2">
            <span className="text-xs text-tx-muted">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, totalCount)} of {totalCount} clients
            </span>
            {totalPages > 1 && (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded px-2 py-1 text-xs font-medium text-primary-text transition hover:bg-primary-subtle disabled:opacity-40"
                >
                  Prev
                </button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 7) {
                    pageNum = i + 1;
                  } else if (page <= 4) {
                    pageNum = i + 1;
                  } else if (page >= totalPages - 3) {
                    pageNum = totalPages - 6 + i;
                  } else {
                    pageNum = page - 3 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                        pageNum === page
                          ? "bg-primary text-white"
                          : "text-primary-text hover:bg-primary-subtle"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded px-2 py-1 text-xs font-medium text-primary-text transition hover:bg-primary-subtle disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
