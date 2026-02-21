import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Entity {
  id: string;
  name: string;
  entity_type: string;
}

interface TaxYear {
  id: string;
  year: number;
  status: string;
  tax_return_id: string | null;
}

interface ClientData {
  id: string;
  name: string;
  status: string;
  entities?: Entity[];
  created_at?: string;
}

// Enriched row for the table — one row per client, with rolled-up info
interface ClientRow {
  id: string;
  name: string;
  status: string;
  entityCount: number;
  primaryEntity: string;
  entityType: string;
  latestYear: number | null;
  returnStatus: string;
  returnId: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type SortField = "name" | "entityType" | "latestYear" | "returnStatus" | "status";
type SortDir = "asc" | "desc";

const STATUS_OPTIONS = ["all", "active", "inactive"] as const;
const RETURN_STATUS_OPTIONS = [
  "all", "no_return", "draft", "in_progress", "in_review", "approved", "filed"
] as const;

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function Clients() {
  const [clients, setClients] = useState<ClientData[]>([]);
  const [entities, setEntities] = useState<Record<string, Entity[]>>({});
  const [taxYears, setTaxYears] = useState<Record<string, TaxYear[]>>({});
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [returnStatusFilter, setReturnStatusFilter] = useState<string>("all");

  // Sort
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // New client form
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  // ---- Data fetching ----

  useEffect(() => {
    async function loadAll() {
      const clientRes = await get("/clients/");
      if (!clientRes.ok) { setLoading(false); return; }

      const allClients = clientRes.data as ClientData[];
      setClients(allClients);

      // Fetch entities for each client in parallel
      const entResults = await Promise.all(
        allClients.map((c) =>
          get(`/entities/?client=${c.id}`).then((r) => ({
            clientId: c.id,
            entities: r.ok ? (r.data as Entity[]) : [],
          }))
        )
      );

      const entMap: Record<string, Entity[]> = {};
      const allEnts: { clientId: string; entity: Entity }[] = [];
      for (const r of entResults) {
        entMap[r.clientId] = r.entities;
        for (const e of r.entities) {
          allEnts.push({ clientId: r.clientId, entity: e });
        }
      }
      setEntities(entMap);

      // Fetch tax years for all entities
      const tyResults = await Promise.all(
        allEnts.map((item) =>
          get(`/tax-years/?entity=${item.entity.id}`).then((r) => ({
            entityId: item.entity.id,
            taxYears: r.ok ? (r.data as TaxYear[]) : [],
          }))
        )
      );

      const tyMap: Record<string, TaxYear[]> = {};
      for (const r of tyResults) {
        tyMap[r.entityId] = r.taxYears;
      }
      setTaxYears(tyMap);
      setLoading(false);
    }
    loadAll();
  }, []);

  // ---- Build enriched rows ----

  const rows: ClientRow[] = clients.map((c) => {
    const ents = entities[c.id] || [];
    const primaryEnt = ents[0];
    const allTY = ents.flatMap((e) => taxYears[e.id] || []);
    const latestTY = allTY.sort((a, b) => b.year - a.year)[0];

    return {
      id: c.id,
      name: c.name,
      status: c.status,
      entityCount: ents.length,
      primaryEntity: primaryEnt?.name || "\u2014",
      entityType: primaryEnt?.entity_type?.replace("_", "-")?.toUpperCase() || "\u2014",
      latestYear: latestTY?.year ?? null,
      returnStatus: latestTY?.tax_return_id
        ? latestTY.status
        : latestTY
          ? "no_return"
          : "\u2014",
      returnId: latestTY?.tax_return_id ?? null,
      created_at: c.created_at || "",
    };
  });

  // ---- Filter ----

  const filtered = rows.filter((r) => {
    if (search && !r.name.toLowerCase().includes(search.toLowerCase()) &&
        !r.primaryEntity.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (returnStatusFilter !== "all" && r.returnStatus !== returnStatusFilter) return false;
    return true;
  });

  // ---- Sort ----

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    const av = a[sortField];
    const bv = b[sortField];
    if (av == null && bv == null) cmp = 0;
    else if (av == null) cmp = 1;
    else if (bv == null) cmp = -1;
    else if (typeof av === "number" && typeof bv === "number") cmp = av - bv;
    else cmp = String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  });

  // ---- Actions ----

  async function handleCreateClient(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    setCreating(true);
    const res = await post("/clients/", { name: trimmed });
    setCreating(false);
    if (res.ok) {
      setClients((prev) =>
        [...prev, res.data as ClientData].sort((a, b) => a.name.localeCompare(b.name))
      );
      setNewName("");
      setShowNew(false);
    } else {
      alert("Failed to create client.");
    }
  }

  async function handleDeleteClient(clientId: string, clientName: string) {
    if (
      !confirm(
        `Delete client "${clientName}" and ALL its entities, tax years, and returns? This cannot be undone.`
      )
    )
      return;
    const res = await del(`/clients/${clientId}/`);
    if (res.ok) {
      setClients((prev) => prev.filter((c) => c.id !== clientId));
    } else {
      alert("Failed to delete client.");
    }
  }

  // ---- Render ----

  return (
    <div>
      {/* Page header with actions */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-tx">Client Manager</h1>
          <p className="text-sm text-tx-secondary">
            {loading ? "Loading..." : `${filtered.length} of ${rows.length} clients`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNew(true)}
            className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover"
          >
            + New Client
          </button>
        </div>
      </div>

      {/* New client form */}
      {showNew && (
        <form
          onSubmit={handleCreateClient}
          className="mb-4 flex items-center gap-2 rounded-lg border border-success/30 bg-success/5 p-3"
        >
          <input
            autoFocus
            type="text"
            placeholder="Client name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full max-w-sm rounded-md border border-input-border bg-input px-3 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
          />
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create"}
          </button>
          <button
            type="button"
            onClick={() => { setShowNew(false); setNewName(""); }}
            className="rounded-lg px-3 py-2 text-sm font-medium text-tx-secondary transition hover:bg-surface-alt"
          >
            Cancel
          </button>
        </form>
      )}

      {/* Filters toolbar */}
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 shadow-sm">
        <input
          type="text"
          placeholder="Search clients or entities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-md border border-input-border bg-input px-3 py-1.5 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
        />

        <div className="h-5 w-px bg-border" />

        <label className="flex items-center gap-1.5 text-xs text-tx-secondary">
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded border border-input-border bg-input px-2 py-1 text-sm text-tx"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o === "all" ? "All" : o.charAt(0).toUpperCase() + o.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-tx-secondary">
          Return
          <select
            value={returnStatusFilter}
            onChange={(e) => setReturnStatusFilter(e.target.value)}
            className="rounded border border-input-border bg-input px-2 py-1 text-sm text-tx"
          >
            {RETURN_STATUS_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o === "all"
                  ? "All"
                  : o === "no_return"
                    ? "No Return"
                    : o.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
        </label>

        {(search || statusFilter !== "all" || returnStatusFilter !== "all") && (
          <button
            onClick={() => {
              setSearch("");
              setStatusFilter("all");
              setReturnStatusFilter("all");
            }}
            className="text-xs text-primary-text hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-tx-secondary">Loading clients...</p>
      ) : sorted.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            {search || statusFilter !== "all" || returnStatusFilter !== "all"
              ? "No clients match your filters."
              : "No clients yet. Click '+ New Client' to get started."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <table className="min-w-full divide-y divide-border zebra-table">
            <thead className="bg-surface-alt">
              <tr>
                <SortableHeader field="name" label="Client" current={sortField} dir={sortDir} onSort={toggleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Entity
                </th>
                <SortableHeader field="entityType" label="Type" current={sortField} dir={sortDir} onSort={toggleSort} />
                <SortableHeader field="latestYear" label="Tax Year" current={sortField} dir={sortDir} onSort={toggleSort} />
                <SortableHeader field="returnStatus" label="Return Status" current={sortField} dir={sortDir} onSort={toggleSort} />
                <SortableHeader field="status" label="Client Status" current={sortField} dir={sortDir} onSort={toggleSort} />
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {sorted.map((r) => (
                <tr key={r.id} className="hover:bg-card-hover transition">
                  {/* Client name */}
                  <td className="px-4 py-3">
                    <Link
                      to={`/clients/${r.id}`}
                      className="text-sm font-semibold text-primary-text hover:underline"
                    >
                      {r.name}
                    </Link>
                  </td>

                  {/* Entity */}
                  <td className="px-4 py-3 text-sm text-tx">
                    {r.primaryEntity}
                    {r.entityCount > 1 && (
                      <span className="ml-1.5 text-xs text-tx-muted">
                        +{r.entityCount - 1} more
                      </span>
                    )}
                  </td>

                  {/* Type */}
                  <td className="px-4 py-3">
                    <span className="rounded bg-surface-alt px-2 py-0.5 text-xs font-medium text-tx-secondary">
                      {r.entityType}
                    </span>
                  </td>

                  {/* Tax Year */}
                  <td className="px-4 py-3 text-sm tabular-nums text-tx">
                    {r.latestYear ?? "\u2014"}
                  </td>

                  {/* Return Status */}
                  <td className="px-4 py-3">
                    <ReturnStatusPill status={r.returnStatus} />
                  </td>

                  {/* Client Status */}
                  <td className="px-4 py-3">
                    <StatusPill status={r.status} />
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/clients/${r.id}`}
                        className="rounded-lg bg-primary-subtle px-2.5 py-1 text-xs font-medium text-primary-text transition hover:bg-primary-subtle/80"
                      >
                        Open
                      </Link>
                      {r.returnId && (
                        <Link
                          to={`/tax-returns/${r.returnId}/editor`}
                          className="rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-white transition hover:bg-primary-hover"
                        >
                          Edit Return
                        </Link>
                      )}
                      <button
                        onClick={() => handleDeleteClient(r.id, r.name)}
                        className="rounded-lg px-2.5 py-1 text-xs font-medium text-danger transition hover:bg-danger-subtle hover:text-danger-hover"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Table footer */}
          <div className="flex items-center justify-between border-t border-border bg-surface-alt px-4 py-2">
            <span className="text-xs text-tx-muted">
              Showing {sorted.length} of {rows.length} clients
            </span>
            <span className="text-xs text-tx-muted">
              Sort: {sortField} ({sortDir})
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
  field,
  label,
  current,
  dir,
  onSort,
}: {
  field: SortField;
  label: string;
  current: SortField;
  dir: SortDir;
  onSort: (f: SortField) => void;
}) {
  const isActive = current === field;
  return (
    <th
      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary cursor-pointer select-none hover:text-tx"
      onClick={() => onSort(field)}
    >
      {label}
      {isActive && (
        <span className="ml-1 text-primary-text">
          {dir === "asc" ? "\u25B2" : "\u25BC"}
        </span>
      )}
    </th>
  );
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-primary-subtle text-primary-text",
    inactive: "bg-surface-alt text-tx-secondary",
  };
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] || colors.active
      }`}
    >
      {status}
    </span>
  );
}

function ReturnStatusPill({ status }: { status: string }) {
  const config: Record<string, { bg: string; label: string }> = {
    "\u2014":     { bg: "bg-surface-alt text-tx-muted",        label: "\u2014" },
    no_return:    { bg: "bg-surface-alt text-tx-secondary",    label: "No Return" },
    draft:        { bg: "bg-surface-alt text-tx-secondary",    label: "Draft" },
    in_progress:  { bg: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", label: "In Progress" },
    in_review:    { bg: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", label: "In Review" },
    approved:     { bg: "bg-primary-subtle text-primary-text", label: "Approved" },
    filed:        { bg: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400", label: "Filed" },
  };
  const c = config[status] || config["\u2014"];
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${c.bg}`}>
      {c.label}
    </span>
  );
}
