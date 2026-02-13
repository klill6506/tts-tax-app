import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/clients", label: "Clients" },
];

export default function AppShell() {
  const { user, logout } = useAuth();

  const firmName = user?.memberships?.[0]?.firm_name ?? "—";

  return (
    <div className="flex h-screen flex-col">
      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
        {/* Left: Brand */}
        <div className="flex items-center gap-6">
          <span className="text-lg font-bold tracking-tight text-blue-600">
            TTS Tax Prep
          </span>

          {/* Nav */}
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right: Firm + user + logout */}
        <div className="flex items-center gap-4">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            {firmName}
          </span>
          <span className="text-sm text-slate-600">
            {user?.first_name || user?.username}
          </span>
          <button
            onClick={logout}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:bg-red-50 hover:text-red-600"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-auto bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
