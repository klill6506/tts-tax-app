import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { get, post, del } from "../lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientData {
  id: string;
  name: string;
}

interface EntityData {
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
// Entity Detail — tax years, trial balance, returns
// ---------------------------------------------------------------------------

export default function EntityDetail() {
  const { clientId, entityId } = useParams<{ clientId: string; entityId: string }>();
  const navigate = useNavigate();

  const [client, setClient] = useState<ClientData | null>(null);
  const [entity, setEntity] = useState<EntityData | null>(null);
  const [taxYears, setTaxYears] = useState<TaxYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingReturn, setCreatingReturn] = useState<string | null>(null);

  // New tax year form
  const [showNewTaxYear, setShowNewTaxYear] = useState(false);
  const [newTaxYearValue, setNewTaxYearValue] = useState(String(new Date().getFullYear()));
  const [creatingTaxYear, setCreatingTaxYear] = useState(false);

  // ---- Data fetching ----

  useEffect(() => {
    if (!clientId || !entityId) return;
    loadData();
  }, [clientId, entityId]);

  async function loadData() {
    if (!clientId || !entityId) return;
    const [clientRes, entityRes, taxYearsRes] = await Promise.all([
      get(`/clients/${clientId}/`),
      get(`/entities/${entityId}/`),
      get(`/tax-years/?entity=${entityId}`),
    ]);

    if (clientRes.ok) setClient(clientRes.data as ClientData);
    if (entityRes.ok) setEntity(entityRes.data as EntityData);
    if (taxYearsRes.ok) setTaxYears(taxYearsRes.data as TaxYear[]);
    setLoading(false);
  }

  // ---- Create tax year ----

  async function handleCreateTaxYear(e: React.FormEvent) {
    e.preventDefault();
    const year = parseInt(newTaxYearValue, 10);
    if (isNaN(year) || year < 2000 || year > 2099) {
      alert("Please enter a valid year (2000-2099).");
      return;
    }
    setCreatingTaxYear(true);
    const res = await post("/tax-years/", {
      entity: entityId,
      year,
      status: "draft",
    });
    setCreatingTaxYear(false);
    if (res.ok) {
      const created = res.data as TaxYear;
      setTaxYears((prev) => [created, ...prev].sort((a, b) => b.year - a.year));
      setShowNewTaxYear(false);
      setNewTaxYearValue(String(new Date().getFullYear()));
    } else {
      const err = res.data as { detail?: string; year?: string[] };
      alert(err.year?.[0] || err.detail || "Failed to create tax year.");
    }
  }

  // ---- Start return ----

  async function handleStartReturn(taxYearId: string) {
    setCreatingReturn(taxYearId);
    const res = await post("/tax-returns/create/", { tax_year: taxYearId });
    setCreatingReturn(null);
    if (res.ok) {
      const created = res.data as { id: string };
      navigate(`/tax-returns/${created.id}/editor`);
    } else {
      const err = res.data as { error?: string };
      alert(err.error || "Failed to create return.");
    }
  }

  // ---- Delete return ----

  async function handleDeleteReturn(taxYearId: string, returnId: string) {
    if (!confirm("Delete this tax return? All field values will be permanently lost.")) return;
    const res = await del(`/tax-returns/${returnId}/`);
    if (res.ok) {
      setTaxYears((prev) =>
        prev.map((ty) =>
          ty.id === taxYearId ? { ...ty, tax_return_id: null } : ty
        )
      );
    } else {
      alert("Failed to delete return.");
    }
  }

  // ---- Delete tax year ----

  async function handleDeleteTaxYear(taxYearId: string, year: number) {
    if (!confirm(`Delete tax year ${year} and its return? This cannot be undone.`)) return;
    const res = await del(`/tax-years/${taxYearId}/`);
    if (res.ok) {
      setTaxYears((prev) => prev.filter((ty) => ty.id !== taxYearId));
    } else {
      alert("Failed to delete tax year.");
    }
  }

  // ---- Render ----

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!client || !entity) return <p className="text-sm text-red-600">Entity not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-slate-500">
        <Link to="/" className="text-blue-600 hover:underline">Client Manager</Link>
        <span className="mx-2">/</span>
        <Link to={`/clients/${clientId}`} className="text-blue-600 hover:underline">{client.name}</Link>
        <span className="mx-2">/</span>
        <span className="font-medium text-slate-800">{entity.name}</span>
      </div>

      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{entity.name}</h1>
          <p className="text-sm text-slate-500">
            {entityTypeLabel(entity.entity_type)} &mdash; {taxYears.length}{" "}
            {taxYears.length === 1 ? "tax year" : "tax years"}
          </p>
        </div>
        <button
          onClick={() => setShowNewTaxYear(true)}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
        >
          + Add Tax Year
        </button>
      </div>

      {/* Entity info card */}
      <div className="mb-5 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-6">
          <div>
            <span className="text-xs font-medium uppercase text-slate-400">Client</span>
            <p className="text-sm font-medium text-slate-800">{client.name}</p>
          </div>
          <div className="h-8 w-px bg-slate-200" />
          <div>
            <span className="text-xs font-medium uppercase text-slate-400">Entity Type</span>
            <p className="text-sm font-medium text-slate-800">
              {entityTypeLabel(entity.entity_type)}
            </p>
          </div>
          <div className="h-8 w-px bg-slate-200" />
          <div>
            <span className="text-xs font-medium uppercase text-slate-400">Tax Years</span>
            <p className="text-sm font-medium text-slate-800">{taxYears.length}</p>
          </div>
        </div>
      </div>

      {/* New tax year form */}
      {showNewTaxYear && (
        <form
          onSubmit={handleCreateTaxYear}
          className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4"
        >
          <div className="flex items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Tax Year
              </label>
              <input
                autoFocus
                type="number"
                min={2000}
                max={2099}
                value={newTaxYearValue}
                onChange={(e) => setNewTaxYearValue(e.target.value)}
                className="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm tabular-nums shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <button
              type="submit"
              disabled={creatingTaxYear}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
            >
              {creatingTaxYear ? "Creating..." : "Create"}
            </button>
            <button
              type="button"
              onClick={() => setShowNewTaxYear(false)}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Tax years table */}
      {taxYears.length === 0 && !showNewTaxYear ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-slate-500">
            No tax years yet. Click "+ Add Tax Year" to get started.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Tax Year</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Return</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {taxYears.map((ty, idx) => (
                <tr key={ty.id} className={`transition hover:bg-blue-50 ${idx % 2 === 1 ? "bg-slate-50/70" : ""}`}>
                  <td className="px-4 py-3">
                    <span className="text-sm font-semibold text-slate-900">
                      {ty.year}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ReturnStatusPill status={ty.status} />
                  </td>
                  <td className="px-4 py-3">
                    {ty.tax_return_id ? (
                      <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                        Active
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">No return</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/tax-years/${ty.id}/trial-balance`}
                        className="rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition hover:bg-blue-100"
                      >
                        Trial Balance
                      </Link>
                      {ty.tax_return_id ? (
                        <>
                          <Link
                            to={`/tax-returns/${ty.tax_return_id}/editor`}
                            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700"
                          >
                            Open Return
                          </Link>
                          <button
                            onClick={() => handleDeleteReturn(ty.id, ty.tax_return_id!)}
                            className="rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100"
                          >
                            Delete Return
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleStartReturn(ty.id)}
                          disabled={creatingReturn === ty.id}
                          className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
                        >
                          {creatingReturn === ty.id ? "Creating..." : "Start Return"}
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteTaxYear(ty.id, ty.year)}
                        className="rounded-md px-2.5 py-1.5 text-xs font-medium text-red-500 transition hover:bg-red-50 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-slate-200 bg-slate-50 px-4 py-2">
            <span className="text-xs text-slate-400">
              {taxYears.length} {taxYears.length === 1 ? "tax year" : "tax years"}
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
