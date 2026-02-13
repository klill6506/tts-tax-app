import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { get, post, del } from "../lib/api";

interface TaxYear {
  id: string;
  year: number;
  status: string;
  tax_return_id: string | null;
}

interface Entity {
  id: string;
  name: string;
  entity_type: string;
}

interface ClientData {
  id: string;
  name: string;
  status: string;
}

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientData | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [taxYears, setTaxYears] = useState<Record<string, TaxYear[]>>({});
  const [loading, setLoading] = useState(true);
  const [creatingReturn, setCreatingReturn] = useState<string | null>(null);

  useEffect(() => {
    if (!clientId) return;
    Promise.all([
      get(`/clients/${clientId}/`),
      get(`/entities/?client=${clientId}`),
    ]).then(([clientRes, entitiesRes]) => {
      if (clientRes.ok) setClient(clientRes.data as ClientData);
      if (entitiesRes.ok) {
        const ents = entitiesRes.data as Entity[];
        setEntities(ents);
        // Fetch tax years for each entity
        Promise.all(
          ents.map((e) => get(`/tax-years/?entity=${e.id}`).then((r) => ({ entityId: e.id, data: r })))
        ).then((results) => {
          const map: Record<string, TaxYear[]> = {};
          for (const r of results) {
            if (r.data.ok) map[r.entityId] = r.data.data as TaxYear[];
          }
          setTaxYears(map);
          setLoading(false);
        });
      } else {
        setLoading(false);
      }
    });
  }, [clientId]);

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

  async function handleDeleteReturn(taxYearId: string, returnId: string) {
    if (!confirm("Delete this tax return? All field values will be permanently lost.")) return;
    const res = await del(`/tax-returns/${returnId}/`);
    if (res.ok) {
      // Update local state: clear the tax_return_id for this tax year
      setTaxYears((prev) => {
        const next = { ...prev };
        for (const eid of Object.keys(next)) {
          next[eid] = next[eid].map((ty) =>
            ty.id === taxYearId ? { ...ty, tax_return_id: null } : ty
          );
        }
        return next;
      });
    } else {
      alert("Failed to delete return.");
    }
  }

  async function handleDeleteEntity(entityId: string, entityName: string) {
    if (!confirm(`Delete entity "${entityName}" and all its tax years/returns? This cannot be undone.`)) return;
    const res = await del(`/entities/${entityId}/`);
    if (res.ok) {
      setEntities((prev) => prev.filter((e) => e.id !== entityId));
      setTaxYears((prev) => {
        const next = { ...prev };
        delete next[entityId];
        return next;
      });
    } else {
      alert("Failed to delete entity.");
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!client) return <p className="text-sm text-red-600">Client not found.</p>;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 text-sm text-slate-500">
        <Link to="/clients" className="text-blue-600 hover:underline">Clients</Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">{client.name}</span>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-slate-900">{client.name}</h1>

      {entities.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-slate-500">No entities yet.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {entities.map((entity) => (
            <div key={entity.id} className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{entity.name}</h2>
                  <p className="text-xs uppercase text-slate-500">{entity.entity_type}</p>
                </div>
                <button
                  onClick={() => handleDeleteEntity(entity.id, entity.name)}
                  className="rounded-md px-2.5 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50 hover:text-red-700"
                >
                  Delete Entity
                </button>
              </div>

              {/* Tax years */}
              {(taxYears[entity.id] || []).length === 0 ? (
                <div className="p-4 text-sm text-slate-500">No tax years.</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {(taxYears[entity.id] || []).map((ty) => (
                    <div key={ty.id} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
                      <div>
                        <span className="text-sm font-medium text-slate-900">
                          Tax Year {ty.year}
                        </span>
                        <ReturnStatusPill status={ty.status} />
                      </div>
                      <div className="flex gap-2">
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
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReturnStatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-slate-100 text-slate-600",
    in_progress: "bg-amber-50 text-amber-700",
    in_review: "bg-amber-50 text-amber-700",
    approved: "bg-blue-50 text-blue-700",
    filed: "bg-green-50 text-green-700",
  };
  return (
    <span className={`ml-2 rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] || colors.draft}`}>
      {status.replace("_", " ")}
    </span>
  );
}
