import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { get, post, del } from "../lib/api";

interface Entity {
  id: string;
  name: string;
  entity_type: string;
}

interface ClientData {
  id: string;
  name: string;
  status: string;
  entities?: Entity[];
}

export default function Clients() {
  const [clients, setClients] = useState<ClientData[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    get("/clients/").then((res) => {
      if (res.ok) setClients(res.data as ClientData[]);
      setLoading(false);
    });
  }, []);

  async function handleCreateClient(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newName.trim();
    if (!trimmed) return;
    setCreating(true);
    const res = await post("/clients/", { name: trimmed });
    setCreating(false);
    if (res.ok) {
      setClients((prev) => [...prev, res.data as ClientData].sort((a, b) => a.name.localeCompare(b.name)));
      setNewName("");
      setShowNew(false);
    } else {
      alert("Failed to create client.");
    }
  }

  async function handleDeleteClient(clientId: string, clientName: string) {
    if (!confirm(`Delete client "${clientName}" and ALL its entities, tax years, and returns? This cannot be undone.`)) return;
    const res = await del(`/clients/${clientId}/`);
    if (res.ok) {
      setClients((prev) => prev.filter((c) => c.id !== clientId));
    } else {
      alert("Failed to delete client.");
    }
  }

  const filtered = clients.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Clients</h1>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
        >
          New Client
        </button>
      </div>

      {/* Inline new-client form */}
      {showNew && (
        <form onSubmit={handleCreateClient} className="mb-4 flex items-center gap-2">
          <input
            autoFocus
            type="text"
            placeholder="Client name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full max-w-sm rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create"}
          </button>
          <button
            type="button"
            onClick={() => { setShowNew(false); setNewName(""); }}
            className="rounded-md px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100"
          >
            Cancel
          </button>
        </form>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        />
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-slate-500">
            {search ? "No clients match your search." : "No clients yet."}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Status
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm font-medium text-slate-900">
                    {c.name}
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <Link
                        to={`/clients/${c.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => handleDeleteClient(c.id, c.name)}
                        className="text-sm font-medium text-red-500 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-blue-50 text-blue-700",
    inactive: "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] || colors.active}`}>
      {status}
    </span>
  );
}
