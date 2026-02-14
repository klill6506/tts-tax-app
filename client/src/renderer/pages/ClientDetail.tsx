import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientData {
  id: string;
  name: string;
  status: string;
}

interface Entity {
  id: string;
  name: string;
  entity_type: string;
}

interface TaxYearSummary {
  id: string;
  year: number;
  status: string;
}

const ENTITY_TYPES = [
  { value: "scorp", label: "S-Corp (1120-S)" },
  { value: "partnership", label: "Partnership (1065)" },
  { value: "ccorp", label: "C-Corp (1120)" },
  { value: "trust", label: "Trust (1041)" },
  { value: "individual", label: "Individual (1040)" },
];

function entityTypeLabel(value: string) {
  return ENTITY_TYPES.find((t) => t.value === value)?.label || value.toUpperCase();
}

// ---------------------------------------------------------------------------
// Entity Manager — shows entities for a single client
// ---------------------------------------------------------------------------

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const [client, setClient] = useState<ClientData | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [taxYearCounts, setTaxYearCounts] = useState<Record<string, TaxYearSummary[]>>({});
  const [loading, setLoading] = useState(true);

  // New entity form
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("scorp");
  const [creating, setCreating] = useState(false);

  // Search
  const [search, setSearch] = useState("");

  // ---- Data fetching ----

  useEffect(() => {
    if (!clientId) return;
    loadData();
  }, [clientId]);

  async function loadData() {
    if (!clientId) return;
    const [clientRes, entitiesRes] = await Promise.all([
      get(`/clients/${clientId}/`),
      get(`/entities/?client=${clientId}`),
    ]);

    if (clientRes.ok) setClient(clientRes.data as ClientData);
    if (entitiesRes.ok) {
      const ents = entitiesRes.data as Entity[];
      setEntities(ents);

      // Fetch tax year counts per entity
      const results = await Promise.all(
        ents.map((e) =>
          get(`/tax-years/?entity=${e.id}`).then((r) => ({
            entityId: e.id,
            taxYears: r.ok ? (r.data as TaxYearSummary[]) : [],
          }))
        )
      );
      const map: Record<string, TaxYearSummary[]> = {};
      for (const r of results) map[r.entityId] = r.taxYears;
      setTaxYearCounts(map);
    }
    setLoading(false);
  }

  // ---- Create entity ----

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed || !clientId) return;
    setCreating(true);
    const res = await post("/entities/", {
      client: clientId,
      name: trimmed,
      entity_type: newType,
    });
    setCreating(false);
    if (res.ok) {
      const created = res.data as Entity;
      setEntities((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setTaxYearCounts((prev) => ({ ...prev, [created.id]: [] }));
      setNewName("");
      setNewType("scorp");
      setShowNew(false);
    } else {
      alert("Failed to create entity.");
    }
  }

  // ---- Delete entity ----

  async function handleDelete(entityId: string, entityName: string) {
    if (!confirm(`Delete "${entityName}" and ALL tax years and returns? This cannot be undone.`)) return;
    const res = await del(`/entities/${entityId}/`);
    if (res.ok) {
      setEntities((prev) => prev.filter((e) => e.id !== entityId));
      setTaxYearCounts((prev) => {
        const next = { ...prev };
        delete next[entityId];
        return next;
      });
    } else {
      alert("Failed to delete entity.");
    }
  }

  // ---- Derived data ----

  const filtered = entities.filter(
    (e) => !search || e.name.toLowerCase().includes(search.toLowerCase())
  );

  // ---- Render ----

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!client) return <p className="text-sm text-red-600">Client not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-slate-500">
        <Link to="/" className="text-blue-600 hover:underline">Client Manager</Link>
        <span className="mx-2">/</span>
        <span className="font-medium text-slate-800">{client.name}</span>
      </div>

      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Entity Manager</h1>
          <p className="text-sm text-slate-500">
            {client.name} &mdash; {loading ? "Loading..." : `${filtered.length} entities`}
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
        >
          + New Entity
        </button>
      </div>

      {/* New entity form */}
      {showNew && (
        <form
          onSubmit={handleCreate}
          className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4"
        >
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Entity Name
              </label>
              <input
                autoFocus
                type="text"
                placeholder="e.g. Acme Corp, Gates Personal..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Entity Type
              </label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                {ENTITY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating || !newName.trim()}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Entity"}
            </button>
            <button
              type="button"
              onClick={() => { setShowNew(false); setNewName(""); }}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Search */}
      {entities.length > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-2.5 shadow-sm">
          <input
            type="text"
            placeholder="Search entities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64 rounded-md border border-slate-300 px-3 py-1.5 text-sm shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
          {search && (
            <button onClick={() => setSearch("")} className="text-xs text-blue-600 hover:underline">Clear</button>
          )}
        </div>
      )}

      {/* Table */}
      {filtered.length === 0 && !showNew ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-slate-500">
            {search
              ? "No entities match your search."
              : "No entities yet. Click '+ New Entity' to create the first filing entity for this client."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Entity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Tax Years</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Latest Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((entity, idx) => {
                const tys = taxYearCounts[entity.id] || [];
                const latestTy = tys.length > 0 ? tys[0] : null; // already sorted -year from server
                return (
                  <tr key={entity.id} className={`transition hover:bg-blue-50 ${idx % 2 === 1 ? "bg-slate-50/70" : ""}`}>
                    <td className="px-4 py-3">
                      <Link
                        to={`/clients/${clientId}/entities/${entity.id}`}
                        className="text-sm font-semibold text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {entity.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        {entityTypeLabel(entity.entity_type)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm tabular-nums text-slate-700">
                      {tys.length}
                    </td>
                    <td className="px-4 py-3">
                      {latestTy ? (
                        <ReturnStatusPill status={latestTy.status} />
                      ) : (
                        <span className="text-xs text-slate-400">&mdash;</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/clients/${clientId}/entities/${entity.id}`}
                          className="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100"
                        >
                          Open
                        </Link>
                        <button
                          onClick={() => handleDelete(entity.id, entity.name)}
                          className="rounded-md px-2.5 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50 hover:text-red-700"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="border-t border-slate-200 bg-slate-50 px-4 py-2">
            <span className="text-xs text-slate-400">
              Showing {filtered.length} of {entities.length} entities
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

function ReturnStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-600",
    in_progress: "bg-amber-50 text-amber-700",
    in_review: "bg-amber-50 text-amber-700",
    approved: "bg-blue-50 text-blue-700",
    filed: "bg-green-50 text-green-700",
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
