import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientData {
  id: string;
  name: string;
  status: string;
}

interface EntitySummary {
  id: string;
  name: string;
  entity_type: string;
}

interface ClientRow {
  id: string;
  name: string;
  status: string;
  entityCount: number;
  entityTypes: string;
}

// ---------------------------------------------------------------------------
// Client Manager — the home page
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const { user } = useAuth();
  const [clients, setClients] = useState<ClientData[]>([]);
  const [entityCounts, setEntityCounts] = useState<Record<string, EntitySummary[]>>({});
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");

  // New client form
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const firmName = user?.memberships?.[0]?.firm_name ?? "Your firm";

  useEffect(() => {
    async function load() {
      const res = await get("/clients/");
      if (!res.ok) { setLoading(false); return; }

      const all = res.data as ClientData[];
      setClients(all);

      const entResults = await Promise.all(
        all.map((c) =>
          get(`/entities/?client=${c.id}`).then((r) => ({
            clientId: c.id,
            entities: r.ok ? (r.data as EntitySummary[]) : [],
          }))
        )
      );
      const entMap: Record<string, EntitySummary[]> = {};
      for (const r of entResults) entMap[r.clientId] = r.entities;
      setEntityCounts(entMap);
      setLoading(false);
    }
    load();
  }, []);

  const rows: ClientRow[] = clients.map((c) => {
    const ents = entityCounts[c.id] || [];
    const types = [...new Set(ents.map((e) =>
      e.entity_type?.replace("_", "-")?.toUpperCase() || "\u2014"
    ))];
    return {
      id: c.id,
      name: c.name,
      status: c.status,
      entityCount: ents.length,
      entityTypes: types.join(", ") || "\u2014",
    };
  });

  const filtered = rows.filter((r) =>
    !search || r.name.toLowerCase().includes(search.toLowerCase())
  );

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    setCreating(true);
    const res = await post("/clients/", { name: trimmed });
    setCreating(false);
    if (res.ok) {
      const created = res.data as ClientData;
      setClients((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setEntityCounts((prev) => ({ ...prev, [created.id]: [] }));
      setNewName("");
      setShowNew(false);
    } else {
      alert("Failed to create client.");
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete "${name}" and ALL entities, tax years, and returns?`)) return;
    const res = await del(`/clients/${id}/`);
    if (res.ok) setClients((prev) => prev.filter((c) => c.id !== id));
    else alert("Failed to delete client.");
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Client Manager</h1>
          <p className="text-sm text-tx-secondary">
            {firmName} &mdash; {loading ? "Loading..." : `${filtered.length} clients`}
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
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        />
        {search && (
          <button onClick={() => setSearch("")} className="text-xs text-primary-text hover:underline">Clear</button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-tx-secondary">Loading clients...</p>
      ) : filtered.length === 0 ? (
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
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Entities</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Entity Types</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {filtered.map((r) => (
                <tr key={r.id} className="transition hover:bg-primary-subtle">
                  <td className="px-4 py-3">
                    <Link to={`/clients/${r.id}`} className="text-sm font-semibold text-primary-text hover:underline">
                      {r.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm tabular-nums text-tx">{r.entityCount}</td>
                  <td className="px-4 py-3">
                    {r.entityTypes !== "\u2014" ? (
                      <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">{r.entityTypes}</span>
                    ) : (
                      <span className="text-xs text-tx-muted">\u2014</span>
                    )}
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
          <div className="border-t border-border bg-surface-alt px-4 py-2">
            <span className="text-xs text-tx-muted">Showing {filtered.length} of {rows.length} clients</span>
          </div>
        </div>
      )}
    </div>
  );
}
