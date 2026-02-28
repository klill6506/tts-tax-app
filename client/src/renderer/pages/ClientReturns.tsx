import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientData {
  id: string;
  name: string;
  status: string;
}

interface ReturnRow {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  tax_year_id: string | null;
  year: number | null;
  tax_year_status: string | null;
  return_id: string | null;
  form_code: string | null;
  return_status: string | null;
  relationship: string;
  ownership_percentage: string | null;
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

function entityTypeShort(value: string) {
  const map: Record<string, string> = {
    scorp: "S-Corp",
    partnership: "Partnership",
    ccorp: "C-Corp",
    trust: "Trust",
    individual: "Individual",
  };
  return map[value] || value;
}

// ---------------------------------------------------------------------------
// Client Returns — shows all returns for an individual client
// ---------------------------------------------------------------------------

export default function ClientReturns() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientData | null>(null);
  const [rows, setRows] = useState<ReturnRow[]>([]);
  const [loading, setLoading] = useState(true);

  // New entity form
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("scorp");
  const [creating, setCreating] = useState(false);

  // New tax year form
  const [addingTaxYear, setAddingTaxYear] = useState<string | null>(null); // entity_id
  const [newYear, setNewYear] = useState(2025);

  useEffect(() => {
    if (!clientId) return;
    loadData();
  }, [clientId]);

  async function loadData() {
    if (!clientId) return;
    setLoading(true);
    const [clientRes, returnsRes] = await Promise.all([
      get(`/clients/${clientId}/`),
      get(`/clients/${clientId}/returns/`),
    ]);
    if (clientRes.ok) setClient(clientRes.data as ClientData);
    if (returnsRes.ok) setRows(returnsRes.data as ReturnRow[]);
    setLoading(false);
  }

  // ---- Start / open return ----

  async function handleStartReturn(taxYearId: string) {
    const res = await post("/tax-returns/create/", { tax_year: taxYearId });
    if (res.ok) {
      const created = res.data as { id: string };
      navigate(`/tax-returns/${created.id}/editor`);
    } else {
      alert("Failed to create return.");
    }
  }

  // ---- Create entity ----

  async function handleCreateEntity(e: React.FormEvent) {
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
      setNewName("");
      setNewType("scorp");
      setShowNew(false);
      loadData(); // refresh
    } else {
      const err = res.data as Record<string, string | string[]>;
      const msg =
        (Array.isArray(err.non_field_errors) ? err.non_field_errors[0] : err.non_field_errors)
        || (Array.isArray(err.name) ? err.name[0] : err.name)
        || "Failed to create entity.";
      alert(msg);
    }
  }

  // ---- Create tax year ----

  async function handleCreateTaxYear(entityId: string) {
    const res = await post("/tax-years/", {
      entity: entityId,
      year: newYear,
      status: "draft",
    });
    if (res.ok) {
      setAddingTaxYear(null);
      loadData();
    } else {
      alert("Failed to create tax year.");
    }
  }

  // ---- Delete entity ----

  async function handleDeleteEntity(entityId: string, entityName: string) {
    if (!confirm(`Delete "${entityName}" and ALL tax years and returns? This cannot be undone.`)) return;
    const res = await del(`/entities/${entityId}/`);
    if (res.ok) loadData();
    else alert("Failed to delete entity.");
  }

  // ---- Group rows by entity ----

  interface EntityGroup {
    entity_id: string;
    entity_name: string;
    entity_type: string;
    relationship: string;
    ownership_percentage: string | null;
    returns: ReturnRow[];
  }

  function groupByEntity(data: ReturnRow[]): EntityGroup[] {
    const map = new Map<string, EntityGroup>();
    for (const row of data) {
      if (!map.has(row.entity_id)) {
        map.set(row.entity_id, {
          entity_id: row.entity_id,
          entity_name: row.entity_name,
          entity_type: row.entity_type,
          relationship: row.relationship,
          ownership_percentage: row.ownership_percentage,
          returns: [],
        });
      }
      map.get(row.entity_id)!.returns.push(row);
    }
    // Sort: individual first, then alphabetical
    return Array.from(map.values()).sort((a, b) => {
      if (a.entity_type === "individual" && b.entity_type !== "individual") return -1;
      if (a.entity_type !== "individual" && b.entity_type === "individual") return 1;
      return a.entity_name.localeCompare(b.entity_name);
    });
  }

  const groups = groupByEntity(rows);
  const entityCount = groups.length;

  // ---- Render ----

  if (loading) return <p className="text-sm text-tx-secondary">Loading...</p>;
  if (!client) return <p className="text-sm text-danger">Client not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-tx-secondary">
        <Link to="/" className="text-primary-text hover:underline">Return Manager</Link>
        <span className="mx-2">/</span>
        <span className="font-medium text-tx">{client.name}</span>
      </div>

      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-tx">{client.name}</h1>
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
            client.status === "active"
              ? "bg-primary-subtle text-primary-text"
              : "bg-surface-alt text-tx-secondary"
          }`}>
            {client.status}
          </span>
          <span className="text-sm text-tx-secondary">
            {entityCount} {entityCount === 1 ? "entity" : "entities"}
          </span>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover"
        >
          + New Entity
        </button>
      </div>

      {/* New entity form */}
      {showNew && (
        <form
          onSubmit={handleCreateEntity}
          className="mb-4 rounded-lg border border-border-subtle bg-card p-4"
        >
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Entity Name</label>
              <input
                autoFocus
                type="text"
                placeholder="e.g. Acme Corp, Smith Partnership..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-tx shadow-sm placeholder:text-tx-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-tx-secondary">Entity Type</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="rounded-md border border-border bg-input px-3 py-2 text-sm text-tx shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
              >
                {ENTITY_TYPES.filter((t) => t.value !== "individual").map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating || !newName.trim()}
              className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white transition hover:bg-success-hover disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Entity"}
            </button>
            <button
              type="button"
              onClick={() => { setShowNew(false); setNewName(""); }}
              className="rounded-lg px-3 py-2 text-sm font-medium text-tx-secondary transition hover:bg-surface-alt"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Returns grouped by entity */}
      {groups.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-tx-secondary">
            No entities yet. Click '+ New Entity' to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.entity_id} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {/* Entity header */}
              <div className="flex items-center justify-between border-b border-border bg-surface-alt px-4 py-3">
                <div className="flex items-center gap-2">
                  <Link
                    to={`/clients/${clientId}/entities/${group.entity_id}`}
                    className="text-sm font-bold text-tx hover:text-primary-text hover:underline"
                  >
                    {group.entity_name}
                  </Link>
                  <span className="rounded bg-surface px-2 py-0.5 text-xs font-medium text-tx-secondary">
                    {entityTypeShort(group.entity_type)}
                  </span>
                  {group.relationship !== "direct" && (
                    <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-xs font-medium text-primary-text">
                      {group.relationship}{group.ownership_percentage ? ` (${parseFloat(group.ownership_percentage)}%)` : ""}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setAddingTaxYear(addingTaxYear === group.entity_id ? null : group.entity_id)}
                    className="rounded-md bg-success px-2.5 py-1 text-xs font-medium text-white transition hover:bg-success-hover"
                  >
                    + Tax Year
                  </button>
                  {group.relationship === "direct" && group.entity_type !== "individual" && (
                    <button
                      onClick={() => handleDeleteEntity(group.entity_id, group.entity_name)}
                      className="rounded-md px-2.5 py-1 text-xs font-medium text-danger transition hover:bg-danger-subtle"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {/* Add tax year inline form */}
              {addingTaxYear === group.entity_id && (
                <div className="flex items-center gap-3 border-b border-border-subtle bg-surface px-4 py-2">
                  <label className="text-xs font-medium text-tx-secondary">Year:</label>
                  <input
                    type="number"
                    value={newYear}
                    onChange={(e) => setNewYear(Number(e.target.value))}
                    className="w-24 rounded-md border border-border bg-input px-2 py-1 text-sm text-tx focus:border-primary focus:outline-none focus:ring-2 focus:ring-focus-ring"
                  />
                  <button
                    onClick={() => handleCreateTaxYear(group.entity_id)}
                    className="rounded-md bg-success px-3 py-1 text-xs font-medium text-white transition hover:bg-success-hover"
                  >
                    Create
                  </button>
                  <button
                    onClick={() => setAddingTaxYear(null)}
                    className="text-xs text-tx-secondary hover:text-tx"
                  >
                    Cancel
                  </button>
                </div>
              )}

              {/* Returns table */}
              {group.returns.some((r) => r.tax_year_id) ? (
                <table className="min-w-full divide-y divide-border-subtle">
                  <thead>
                    <tr className="bg-surface">
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Year</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Form</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-tx-secondary">Status</th>
                      <th className="px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider text-tx-secondary">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {group.returns
                      .filter((r) => r.tax_year_id)
                      .sort((a, b) => (b.year ?? 0) - (a.year ?? 0))
                      .map((r) => (
                        <tr key={r.tax_year_id} className="transition hover:bg-primary-subtle">
                          <td className="px-4 py-2.5 text-sm font-medium tabular-nums text-tx">{r.year}</td>
                          <td className="px-4 py-2.5 text-sm text-tx-secondary">
                            {r.form_code || <span className="text-tx-muted">&mdash;</span>}
                          </td>
                          <td className="px-4 py-2.5">
                            {r.return_status ? (
                              <ReturnStatusPill status={r.return_status} />
                            ) : r.tax_year_status ? (
                              <span className="inline-block rounded-full bg-surface-alt px-2.5 py-0.5 text-xs font-medium text-tx-secondary">
                                {r.tax_year_status.replace("_", " ")}
                              </span>
                            ) : (
                              <span className="text-xs text-tx-muted">&mdash;</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {r.return_id ? (
                                <>
                                  <Link
                                    to={`/tax-returns/${r.return_id}/editor`}
                                    className="rounded-md bg-primary-subtle px-2.5 py-1 text-xs font-medium text-primary-text transition hover:bg-primary hover:text-white"
                                  >
                                    Open
                                  </Link>
                                  <Link
                                    to={`/tax-returns/${r.return_id}/preview`}
                                    className="rounded-md px-2.5 py-1 text-xs font-medium text-tx-secondary transition hover:bg-surface-alt"
                                  >
                                    Preview
                                  </Link>
                                </>
                              ) : r.tax_year_id ? (
                                <button
                                  onClick={() => handleStartReturn(r.tax_year_id!)}
                                  className="rounded-md bg-success px-2.5 py-1 text-xs font-medium text-white transition hover:bg-success-hover"
                                >
                                  Start Return
                                </button>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              ) : (
                <div className="px-4 py-4 text-center text-xs text-tx-muted">
                  No tax years yet. Click '+ Tax Year' to begin.
                </div>
              )}
            </div>
          ))}
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
