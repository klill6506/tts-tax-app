import { useState, useRef, useEffect } from "react";
import { NavLink, Outlet, useNavigate, useLocation, useMatch } from "react-router-dom";
import { useAuth } from "../lib/auth";

// ---------------------------------------------------------------------------
// Menu definitions — placeholder items get functionality later
// ---------------------------------------------------------------------------

interface MenuItem {
  label: string;
  to?: string;          // client-side route
  shortcut?: string;    // keyboard hint (display only)
  divider?: boolean;    // separator line
  disabled?: boolean;   // grayed out placeholder
}

interface MenuGroup {
  label: string;
  items: MenuItem[];
}

const MENUS: MenuGroup[] = [
  {
    label: "File",
    items: [
      { label: "New Return...", shortcut: "Ctrl+N", disabled: true },
      { label: "Open Return...", shortcut: "Ctrl+O", disabled: true },
      { divider: true, label: "" },
      { label: "Import Trial Balance...", disabled: true },
      { label: "Import Prior Year...", disabled: true },
      { divider: true, label: "" },
      { label: "Print / PDF", shortcut: "Ctrl+P", disabled: true },
      { label: "Export to CSV...", disabled: true },
      { divider: true, label: "" },
      { label: "Exit", disabled: true },
    ],
  },
  {
    label: "Clients",
    items: [
      { label: "Client Manager", to: "/" },
      { label: "New Client...", to: "/" },
      { divider: true, label: "" },
      { label: "Client Search...", shortcut: "Ctrl+K", disabled: true },
    ],
  },
  {
    label: "Returns",
    items: [
      { label: "All Returns", to: "/returns", disabled: true },
      { label: "In Progress", disabled: true },
      { label: "Ready for Review", disabled: true },
      { label: "Filed", disabled: true },
      { divider: true, label: "" },
      { label: "Batch Operations...", disabled: true },
    ],
  },
  {
    label: "Tools",
    items: [
      { label: "Mapping Templates", disabled: true },
      { label: "Diagnostics", to: "/tools/diagnostics", disabled: true },
      { label: "Audit Log", to: "/tools/audit-log", disabled: true },
      { divider: true, label: "" },
      { label: "Import / Export", disabled: true },
      { label: "Bulk Print Queue", disabled: true },
    ],
  },
  {
    label: "Reports",
    items: [
      { label: "Season Summary", to: "/reports", disabled: true },
      { label: "Returns by Status", disabled: true },
      { label: "Preparer Workload", disabled: true },
      { label: "Client Listing", disabled: true },
      { divider: true, label: "" },
      { label: "Custom Report Builder", disabled: true },
    ],
  },
  {
    label: "Admin",
    items: [
      { label: "Firm Settings", to: "/admin/firm", disabled: true },
      { label: "User Management", to: "/admin/users", disabled: true },
      { label: "Roles & Permissions", disabled: true },
      { divider: true, label: "" },
      { label: "Form Templates", disabled: true },
      { label: "System Health", disabled: true },
    ],
  },
  {
    label: "Help",
    items: [
      { label: "Getting Started", disabled: true },
      { label: "Keyboard Shortcuts", disabled: true },
      { label: "IRS Reference", disabled: true },
      { divider: true, label: "" },
      { label: "About TTS Tax Prep", disabled: true },
    ],
  },
];

const NAV_TABS = [
  { to: "/", label: "Client Manager", end: true },
];

// ---------------------------------------------------------------------------
// Dropdown menu component
// ---------------------------------------------------------------------------

function DropdownMenu({
  group,
  isOpen,
  onToggle,
  onClose,
  onHover,
}: {
  group: MenuGroup;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
  onHover: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    if (isOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={onToggle}
        onMouseEnter={onHover}
        className={`px-3 py-1 text-xs font-medium rounded transition ${
          isOpen
            ? "bg-blue-600 text-white"
            : "text-slate-300 hover:bg-slate-700 hover:text-white"
        }`}
      >
        {group.label}
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-0.5 min-w-[220px] rounded-md border border-slate-600 bg-slate-800 py-1 shadow-xl">
          {group.items.map((item, i) =>
            item.divider ? (
              <div key={i} className="my-1 border-t border-slate-700" />
            ) : (
              <button
                key={i}
                disabled={item.disabled}
                onClick={() => {
                  onClose();
                  if (item.to) navigate(item.to);
                }}
                className={`flex w-full items-center justify-between px-3 py-1.5 text-left text-sm ${
                  item.disabled
                    ? "text-slate-500 cursor-default"
                    : "text-slate-200 hover:bg-blue-600 hover:text-white"
                }`}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="ml-6 text-xs text-slate-500">
                    {item.shortcut}
                  </span>
                )}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AppShell
// ---------------------------------------------------------------------------

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [anyMenuWasOpened, setAnyMenuWasOpened] = useState(false);

  const firmName = user?.memberships?.[0]?.firm_name ?? "—";

  // Determine "parent" route for hierarchical back navigation
  const isHome = location.pathname === "/";
  const matchClient = useMatch("/clients/:clientId");
  const matchEntity = useMatch("/clients/:clientId/entities/:entityId");
  const matchTB = useMatch("/tax-years/:taxYearId/trial-balance");
  const matchEditor = useMatch("/tax-returns/:taxReturnId/editor");

  let parentRoute: string | null = null;
  if (matchEntity) {
    parentRoute = `/clients/${matchEntity.params.clientId}`;
  } else if (matchClient) {
    parentRoute = "/";
  } else if (matchTB || matchEditor) {
    // These don't have a clean parent without more data, use browser back
    parentRoute = null;
  }

  const canGoBack = !isHome && (parentRoute !== null || location.key !== "default");

  function handleToggle(label: string) {
    if (openMenu === label) {
      setOpenMenu(null);
      setAnyMenuWasOpened(false);
    } else {
      setOpenMenu(label);
      setAnyMenuWasOpened(true);
    }
  }

  function handleHover(label: string) {
    // Only switch menus on hover if one is already open
    if (anyMenuWasOpened && openMenu !== null) {
      setOpenMenu(label);
    }
  }

  function handleClose() {
    setOpenMenu(null);
    setAnyMenuWasOpened(false);
  }

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      {/* ── Menu Bar ── */}
      <div className="flex h-8 shrink-0 items-center border-b border-slate-700 bg-slate-800 px-2 gap-0.5">
        {MENUS.map((group) => (
          <DropdownMenu
            key={group.label}
            group={group}
            isOpen={openMenu === group.label}
            onToggle={() => handleToggle(group.label)}
            onClose={handleClose}
            onHover={() => handleHover(group.label)}
          />
        ))}
      </div>

      {/* ── Primary Toolbar ── */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-slate-700 bg-slate-800 px-4">
        {/* Left: Brand + Nav + Back */}
        <div className="flex items-center gap-4">
          <span className="text-base font-bold tracking-tight text-blue-400">
            TTS Tax Prep
          </span>

          <div className="h-5 w-px bg-slate-700" />

          <nav className="flex gap-0.5">
            {NAV_TABS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-slate-700 text-blue-400"
                      : "text-slate-400 hover:bg-slate-700 hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* Back button — navigates up the hierarchy */}
          {canGoBack && (
            <>
              <div className="h-5 w-px bg-slate-700" />
              <button
                onClick={() => {
                  if (parentRoute) navigate(parentRoute);
                  else navigate(-1);
                }}
                className="flex items-center gap-1.5 rounded-md border border-slate-600 bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300 transition hover:bg-slate-600 hover:text-white"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
                Back
              </button>
            </>
          )}
        </div>

        {/* Right: Tax Year + Firm + User + Actions */}
        <div className="flex items-center gap-3">
          {/* Tax Year selector (display only for now) */}
          <div className="flex items-center gap-1.5 rounded-md border border-slate-600 bg-slate-700 px-2.5 py-1">
            <span className="text-xs font-medium text-slate-400">Tax Year</span>
            <span className="text-sm font-bold text-white">2025</span>
          </div>

          <div className="h-5 w-px bg-slate-700" />

          <span className="rounded-full bg-slate-700 px-2.5 py-0.5 text-xs font-medium text-slate-300">
            {firmName}
          </span>

          <div className="flex items-center gap-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
              {(user?.first_name?.[0] || user?.username?.[0] || "?").toUpperCase()}
            </div>
            <span className="text-sm text-slate-300">
              {user?.first_name || user?.username}
            </span>
          </div>

          <button
            onClick={logout}
            className="rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-red-900/50 hover:text-red-400"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Content + Status Bar ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Content */}
        <main className="flex-1 overflow-auto bg-slate-200 p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>

        {/* Status bar */}
        <footer className="flex h-6 shrink-0 items-center justify-between border-t border-slate-700 bg-slate-800 px-4 text-xs text-slate-500">
          <div className="flex items-center gap-4">
            <span>TTS Tax Prep v0.1.0</span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
              Server connected
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span>Firm: {firmName}</span>
            <span>{user?.username}</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
