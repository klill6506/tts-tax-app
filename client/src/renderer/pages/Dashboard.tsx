import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { get } from "../lib/api";

interface ClientSummary {
  id: string;
  name: string;
  status: string;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get("/clients/").then((res) => {
      if (res.ok) setClients(res.data as ClientSummary[]);
      setLoading(false);
    });
  }, []);

  const firmName = user?.memberships?.[0]?.firm_name ?? "Your firm";

  return (
    <div>
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Welcome back, {user?.first_name || user?.username}
        </h1>
        <p className="text-sm text-slate-500">{firmName}</p>
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
          Quick Actions
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/clients"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            View Clients
          </Link>
        </div>
      </div>

      {/* System status */}
      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
          System Status
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatusCard label="Clients" value={loading ? "..." : String(clients.length)} color="blue" />
          <StatusCard
            label="Active"
            value={loading ? "..." : String(clients.filter((c) => c.status === "active").length)}
            color="green"
          />
          <StatusCard label="Server" value="Connected" color="green" />
        </div>
      </div>

      {/* Recent clients */}
      {clients.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
            Recent Clients
          </h2>
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            {clients.slice(0, 5).map((c) => (
              <Link
                key={c.id}
                to={`/clients/${c.id}`}
                className="flex items-center justify-between border-b border-slate-100 px-4 py-3 last:border-b-0 hover:bg-slate-50"
              >
                <span className="text-sm font-medium text-slate-900">{c.name}</span>
                <StatusPill status={c.status} />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusCard({ label, value, color }: { label: string; value: string; color: "blue" | "green" | "yellow" | "red" }) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 inline-block rounded-md px-2 py-0.5 text-xl font-bold ${colors[color]}`}>
        {value}
      </p>
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
