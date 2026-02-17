import { useState, useRef, useEffect } from "react";
import { NavLink, Outlet, useNavigate, useLocation, useMatch } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";

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
// Theme toggle icons
// ---------------------------------------------------------------------------

function SunIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25A2.25 2.25 0 015.25 3h13.5A2.25 2.25 0 0121 5.25z" />
    </svg>
  );
}

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
            ? "bg-primary text-white"
            : "text-tx-on-dark hover:bg-nav-active hover:text-white"
        }`}
      >
        {group.label}
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-0.5 min-w-[220px] rounded-md border border-nav-border bg-nav py-1 shadow-xl">
          {group.items.map((item, i) =>
            item.divider ? (
              <div key={i} className="my-1 border-t border-nav-border" />
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
                    ? "text-tx-muted cursor-default"
                    : "text-tx-on-dark hover:bg-primary hover:text-white"
                }`}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="ml-6 text-xs text-tx-muted">
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
  const { mode, cycle } = useTheme();
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

  const themeLabel = mode === "light" ? "Light" : mode === "dark" ? "Dark" : "System";

  return (
    <div className="flex h-screen flex-col bg-surface">
      {/* ── Menu Bar ── */}
      <div className="flex h-8 shrink-0 items-center border-b border-nav-border bg-nav px-2 gap-0.5">
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
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-nav-border bg-nav px-4">
        {/* Left: Brand + Nav + Back */}
        <div className="flex items-center gap-4">
          <span className="text-base font-bold tracking-tight text-primary">
            TTS Tax Prep
          </span>

          <div className="h-5 w-px bg-nav-border" />

          <nav className="flex gap-0.5">
            {NAV_TABS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-nav-active text-primary"
                      : "text-tx-muted hover:bg-nav-active hover:text-white"
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
              <div className="h-5 w-px bg-nav-border" />
              <button
                onClick={() => {
                  if (parentRoute) navigate(parentRoute);
                  else navigate(-1);
                }}
                className="flex items-center gap-1.5 rounded-md border border-nav-border bg-nav-active px-3 py-1 text-xs font-medium text-tx-on-dark transition hover:bg-nav hover:text-white"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
                Back
              </button>
            </>
          )}
        </div>

        {/* Right: Theme + Tax Year + Firm + User + Actions */}
        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={cycle}
            title={`Theme: ${themeLabel}`}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-tx-on-dark transition hover:bg-nav-active hover:text-white"
          >
            {mode === "light" && <SunIcon />}
            {mode === "dark" && <MoonIcon />}
            {mode === "system" && <MonitorIcon />}
          </button>

          <div className="h-5 w-px bg-nav-border" />

          {/* Tax Year selector (display only for now) */}
          <div className="flex items-center gap-1.5 rounded-md border border-nav-border bg-nav-active px-2.5 py-1">
            <span className="text-xs font-medium text-tx-muted">Tax Year</span>
            <span className="text-sm font-bold text-white">2025</span>
          </div>

          <div className="h-5 w-px bg-nav-border" />

          <span className="rounded-full bg-nav-active px-2.5 py-0.5 text-xs font-medium text-tx-on-dark">
            {firmName}
          </span>

          <div className="flex items-center gap-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
              {(user?.first_name?.[0] || user?.username?.[0] || "?").toUpperCase()}
            </div>
            <span className="text-sm text-tx-on-dark">
              {user?.first_name || user?.username}
            </span>
          </div>

          <button
            onClick={logout}
            className="rounded-md px-2 py-1 text-xs font-medium text-tx-muted transition hover:bg-danger-subtle hover:text-danger"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Content + Status Bar ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Content */}
        <main className="flex-1 overflow-auto bg-surface p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>

        {/* Status bar */}
        <footer className="flex h-6 shrink-0 items-center justify-between border-t border-nav-border bg-nav px-4 text-xs text-tx-muted">
          <div className="flex items-center gap-4">
            <span>TTS Tax Prep v0.1.0</span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-success" />
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
