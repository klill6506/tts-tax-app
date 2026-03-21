import { useState, useRef, useEffect, type ReactNode } from "react";
import { NavLink, Outlet, useNavigate, useLocation, useMatch } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { get } from "../lib/api";
import AiHelpPanel from "./AiHelpPanel";
import pkg from "../../../package.json";

export type AppShellContext = {
  setEditorBreadcrumb: (node: ReactNode) => void;
};

const CLIENT_VERSION = pkg.version;

// ---------------------------------------------------------------------------
// Menu definitions — placeholder items get functionality later
// ---------------------------------------------------------------------------

interface MenuItem {
  label: string;
  to?: string;          // client-side route
  action?: string;      // named action (e.g. "about")
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
      { label: "New Client...", action: "new-client" },
      { divider: true, label: "" },
      { label: "Client Search...", shortcut: "Ctrl+K", disabled: true },
    ],
  },
  {
    label: "Returns",
    items: [
      { label: "All Returns", to: "/" },
      { divider: true, label: "" },
      { label: "S-Corp Returns (1120-S)", to: "/returns?form=1120-S" },
      { label: "Partnership Returns (1065)", to: "/returns?form=1065" },
      { label: "C-Corp Returns (1120)", to: "/returns?form=1120" },
      { divider: true, label: "" },
      { label: "In Progress", to: "/returns?status=in_progress" },
      { label: "Ready for Review", to: "/returns?status=in_review" },
      { label: "Filed", to: "/returns?status=filed" },
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
      { label: "Preparer Manager", to: "/admin/preparers" },
      { label: "Print Packages", to: "/admin/print-packages" },
      { divider: true, label: "" },
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
      { label: "About TTS Tax Prep", action: "about" },
    ],
  },
];

const NAV_TABS = [
  { to: "/", label: "Return Manager", end: true },
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
  onAction,
}: {
  group: MenuGroup;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
  onHover: () => void;
  onAction?: (action: string) => void;
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
                  if (item.action && onAction) onAction(item.action);
                  else if (item.to) navigate(item.to);
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

// ---------------------------------------------------------------------------
// Theme presets — complete theme in one click
// ---------------------------------------------------------------------------

interface ThemePreset {
  name: string;
  id: string;
  swatch: string;
  tokens: Record<string, string>;
  fontSans: string | null;      // null = keep default (Inter)
  fontHeadline: string | null;   // null = no separate headline font
  themeClass: string | null;     // CSS class added to <html>
}

const THEME_PRESETS: ThemePreset[] = [
  {
    name: "Default",
    id: "default",
    swatch: "#2563eb",
    tokens: {},   // empty = use CSS defaults
    fontSans: null,
    fontHeadline: null,
    themeClass: null,
  },
  {
    name: "Editorial Gold",
    id: "editorial-gold",
    swatch: "#745b00",
    tokens: {
      "--surface": "#f1eee5",
      "--surface-alt": "#e6e2d9",
      "--card": "#fdf9f0",
      "--card-hover": "#f7f3ea",
      "--zebra": "#f7f3ea",
      "--nav": "#493800",
      "--nav-active": "#745b00",
      "--nav-border": "#584400",
      "--border": "#d0c5af",
      "--border-subtle": "#e6e2d9",
      "--input": "#fdf9f0",
      "--input-border": "#7f7663",
      "--tx": "#1c1c17",
      "--tx-secondary": "#4d4635",
      "--tx-muted": "#7f7663",
      "--tx-on-dark": "#fdf9f0",
      "--primary": "#745b00",
      "--primary-hover": "#584400",
      "--primary-subtle": "#ffe08b",
      "--primary-text": "#584400",
      "--accent": "#4259a9",
      "--accent-hover": "#284190",
      "--focus-ring": "#745b0040",
    },
    fontSans: '"Work Sans", "Inter", sans-serif',
    fontHeadline: '"Newsreader", Georgia, serif',
    themeClass: "theme-editorial",
  },
];

// All CSS custom properties that a theme preset can set
const ALL_THEME_TOKENS = [
  "--surface", "--surface-alt", "--card", "--card-hover", "--zebra",
  "--nav", "--nav-active", "--nav-border",
  "--border", "--border-subtle",
  "--input", "--input-border",
  "--tx", "--tx-secondary", "--tx-muted", "--tx-on-dark",
  "--primary", "--primary-hover", "--primary-subtle", "--primary-text",
  "--accent", "--accent-hover",
  "--focus-ring",
];

function applyThemePreset(preset: ThemePreset) {
  const root = document.documentElement;

  // Apply color tokens
  for (const key of ALL_THEME_TOKENS) {
    if (preset.tokens[key]) {
      root.style.setProperty(key, preset.tokens[key]);
    } else {
      root.style.removeProperty(key);
    }
  }

  // Apply fonts
  if (preset.fontSans) {
    root.style.setProperty("--font-sans", preset.fontSans);
  } else {
    root.style.removeProperty("--font-sans");
  }
  if (preset.fontHeadline) {
    root.style.setProperty("--font-headline", preset.fontHeadline);
  } else {
    root.style.removeProperty("--font-headline");
  }

  // Apply theme class
  // Remove all possible theme classes first
  for (const p of THEME_PRESETS) {
    if (p.themeClass) root.classList.remove(p.themeClass);
  }
  if (preset.themeClass) {
    root.classList.add(preset.themeClass);
  }
}

function clearThemePreset() {
  const root = document.documentElement;
  for (const key of ALL_THEME_TOKENS) {
    root.style.removeProperty(key);
  }
  root.style.removeProperty("--font-sans");
  root.style.removeProperty("--font-headline");
  for (const p of THEME_PRESETS) {
    if (p.themeClass) root.classList.remove(p.themeClass);
  }
}

// ---------------------------------------------------------------------------
// Background palette swatches (fine-tuning within default theme)
// ---------------------------------------------------------------------------

interface BgPalette {
  name: string;
  surface: string;
  surfaceAlt: string;
  zebra: string;
}

interface AccentPalette {
  name: string;
  primary: string;
  primaryHover: string;
  primarySubtle: string;
  primaryText: string;
  nav: string;
  navActive: string;
  navBorder: string;
  swatch: string; // preview color for the button
}

const BG_PALETTES: BgPalette[] = [
  { name: "Slate",       surface: "#e2e8f0", surfaceAlt: "#cbd5e1", zebra: "#f1f5f9" },
  { name: "Blue Mist",   surface: "#eef3fa", surfaceAlt: "#dce5f0", zebra: "#f5f8fc" },
  { name: "Warm Stone",  surface: "#f5f4f1", surfaceAlt: "#e8e6e1", zebra: "#faf9f7" },
  { name: "Sage",        surface: "#f0f4f1", surfaceAlt: "#dfe6e0", zebra: "#f7faf7" },
  { name: "Slate Blue",  surface: "#ebeef5", surfaceAlt: "#dde1ec", zebra: "#f3f5fa" },
];

const ACCENT_PALETTES: AccentPalette[] = [
  { name: "Blue",    swatch: "#2563eb", primary: "#2563eb", primaryHover: "#1d4ed8", primarySubtle: "#dbeafe", primaryText: "#1d4ed8", nav: "#1e3a5f", navActive: "#1e40af", navBorder: "#1d4ed8" },
  { name: "Indigo",  swatch: "#4f46e5", primary: "#4f46e5", primaryHover: "#4338ca", primarySubtle: "#e0e7ff", primaryText: "#4338ca", nav: "#312e81", navActive: "#3730a3", navBorder: "#4338ca" },
  { name: "Teal",    swatch: "#0d9488", primary: "#0d9488", primaryHover: "#0f766e", primarySubtle: "#ccfbf1", primaryText: "#0f766e", nav: "#134e4a", navActive: "#115e59", navBorder: "#0f766e" },
  { name: "Violet",  swatch: "#7c3aed", primary: "#7c3aed", primaryHover: "#6d28d9", primarySubtle: "#ede9fe", primaryText: "#6d28d9", nav: "#4c1d95", navActive: "#5b21b6", navBorder: "#6d28d9" },
  { name: "Rose",    swatch: "#e11d48", primary: "#e11d48", primaryHover: "#be123c", primarySubtle: "#ffe4e6", primaryText: "#be123c", nav: "#881337", navActive: "#9f1239", navBorder: "#be123c" },
];

function applyBgPalette(p: BgPalette) {
  const root = document.documentElement;
  root.style.setProperty("--surface", p.surface);
  root.style.setProperty("--surface-alt", p.surfaceAlt);
  root.style.setProperty("--zebra", p.zebra);
}

function clearBgPalette() {
  const root = document.documentElement;
  root.style.removeProperty("--surface");
  root.style.removeProperty("--surface-alt");
  root.style.removeProperty("--zebra");
}

function applyAccentPalette(p: AccentPalette) {
  const root = document.documentElement;
  root.style.setProperty("--primary", p.primary);
  root.style.setProperty("--primary-hover", p.primaryHover);
  root.style.setProperty("--primary-subtle", p.primarySubtle);
  root.style.setProperty("--primary-text", p.primaryText);
  root.style.setProperty("--nav", p.nav);
  root.style.setProperty("--nav-active", p.navActive);
  root.style.setProperty("--nav-border", p.navBorder);
}

function clearAccentPalette() {
  const root = document.documentElement;
  ["--primary", "--primary-hover", "--primary-subtle", "--primary-text", "--nav", "--nav-active", "--nav-border"].forEach(v => root.style.removeProperty(v));
}

export default function AppShell() {
  const { user, logout } = useAuth();
  const { mode, cycle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [anyMenuWasOpened, setAnyMenuWasOpened] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [serverVersion, setServerVersion] = useState<string | null>(null);
  const [showPalettes, setShowPalettes] = useState(false);
  const [activePreset, setActivePreset] = useState(() => {
    const saved = localStorage.getItem("sherpa-theme-preset");
    return saved ?? "default";
  });
  const [activeBg, setActiveBg] = useState(() => {
    const saved = localStorage.getItem("sherpa-bg-palette");
    return saved !== null ? parseInt(saved, 10) : 0;
  });
  const [activeAccent, setActiveAccent] = useState(() => {
    const saved = localStorage.getItem("sherpa-accent-palette");
    return saved !== null ? parseInt(saved, 10) : 0;
  });
  const paletteRef = useRef<HTMLDivElement>(null);

  const firmName = user?.memberships?.[0]?.firm_name ?? "—";
  const [editorBreadcrumb, setEditorBreadcrumb] = useState<ReactNode>(null);

  const isPresetActive = activePreset !== "default";

  // Fetch server version when About dialog opens
  useEffect(() => {
    if (!showAbout) return;
    get("/version/").then((res) => {
      if (res.ok) setServerVersion((res.data as { version: string }).version);
      else setServerVersion("unavailable");
    });
  }, [showAbout]);

  // Restore saved theme on mount — preset takes precedence over bg/accent
  useEffect(() => {
    const savedPreset = localStorage.getItem("sherpa-theme-preset");
    if (savedPreset && savedPreset !== "default") {
      const preset = THEME_PRESETS.find(p => p.id === savedPreset);
      if (preset) {
        applyThemePreset(preset);
        return;  // skip bg/accent restore when a preset is active
      }
    }
    // No preset — restore individual palettes
    if (activeBg > 0 && activeBg < BG_PALETTES.length) applyBgPalette(BG_PALETTES[activeBg]);
    if (activeAccent > 0 && activeAccent < ACCENT_PALETTES.length) applyAccentPalette(ACCENT_PALETTES[activeAccent]);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Close palette dropdown on outside click
  useEffect(() => {
    if (!showPalettes) return;
    function handleClick(e: MouseEvent) {
      if (paletteRef.current && !paletteRef.current.contains(e.target as Node)) {
        setShowPalettes(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showPalettes]);

  function handleMenuAction(action: string) {
    if (action === "about") setShowAbout(true);
    if (action === "new-client") navigate("/?new-client=1");
  }

  // Determine "parent" route for hierarchical back navigation
  const isHome = location.pathname === "/";
  const matchClient = useMatch("/clients/:clientId");
  const matchEntity = useMatch("/clients/:clientId/entities/:entityId");
  const matchTB = useMatch("/tax-years/:taxYearId/trial-balance");
  const matchEditor = useMatch("/tax-returns/:taxReturnId/editor");
  const isInEditor = !!matchEditor;

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
      {/* ── Menu Bar (hidden when inside a return editor) ── */}
      {!isInEditor && (
        <div className="flex h-8 shrink-0 items-center border-b border-nav-border bg-nav px-2 gap-0.5">
          {MENUS.map((group) => (
            <DropdownMenu
              key={group.label}
              group={group}
              isOpen={openMenu === group.label}
              onToggle={() => handleToggle(group.label)}
              onClose={handleClose}
              onHover={() => handleHover(group.label)}
              onAction={handleMenuAction}
            />
          ))}
        </div>
      )}

      {/* ── Primary Toolbar ── */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-nav-border bg-nav px-4">
        {/* Left: Brand + Nav + Back (or breadcrumb when in editor) */}
        <div className="flex items-center gap-4">
          {isInEditor ? (
            <>
              <button
                onClick={() => navigate("/")}
                className="flex items-center gap-1.5 rounded-md border border-nav-border bg-nav-active px-3 py-1 text-xs font-medium text-tx-on-dark transition hover:bg-nav hover:text-white"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
                Back
              </button>
              {editorBreadcrumb && (
                <>
                  <div className="h-5 w-px bg-nav-border" />
                  {editorBreadcrumb}
                </>
              )}
            </>
          ) : (
            <>
              <span className="text-2xl font-extrabold tracking-tight text-white drop-shadow-sm">
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
                      `rounded-md px-3 py-1.5 text-sm font-semibold transition ${
                        isActive
                          ? "bg-nav-active text-white"
                          : "text-tx-on-dark/70 hover:bg-nav-active hover:text-white"
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
            </>
          )}
        </div>

        {/* Right: Theme + Tax Year + Firm + User + Actions */}
        <div className="flex items-center gap-3">
          {/* Theme toggle — hidden when a theme preset overrides colors */}
          {!isPresetActive && (
            <button
              onClick={cycle}
              title={`Theme: ${themeLabel}`}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-tx-on-dark transition hover:bg-nav-active hover:text-white"
            >
              {mode === "light" && <SunIcon />}
              {mode === "dark" && <MoonIcon />}
              {mode === "system" && <MonitorIcon />}
            </button>
          )}

          {/* Palette picker */}
          <div className="relative" ref={paletteRef}>
            <button
              onClick={() => setShowPalettes(!showPalettes)}
              title="Color palette"
              className="flex items-center gap-1 rounded-md px-2 py-1 text-tx-on-dark transition hover:bg-nav-active hover:text-white"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.098 19.902a3.75 3.75 0 005.304 0l6.401-6.402M6.75 21A3.75 3.75 0 013 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 003.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008z" />
              </svg>
            </button>

            {showPalettes && (
              <div className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-border bg-card p-3 shadow-2xl z-50">
                {/* Theme presets section */}
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-tx-muted">Theme</p>
                <div className="flex gap-1.5 mb-2">
                  {THEME_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      onClick={() => {
                        setActivePreset(preset.id);
                        localStorage.setItem("sherpa-theme-preset", preset.id);
                        if (preset.id === "default") {
                          clearThemePreset();
                          // Re-apply saved bg/accent palettes
                          if (activeBg > 0 && activeBg < BG_PALETTES.length) applyBgPalette(BG_PALETTES[activeBg]);
                          if (activeAccent > 0 && activeAccent < ACCENT_PALETTES.length) applyAccentPalette(ACCENT_PALETTES[activeAccent]);
                        } else {
                          applyThemePreset(preset);
                        }
                      }}
                      className={`flex items-center gap-1.5 rounded-lg border-2 px-2.5 py-1.5 text-xs font-medium transition ${
                        activePreset === preset.id
                          ? "border-white ring-2 ring-primary scale-105 bg-primary-subtle text-tx"
                          : "border-border-subtle bg-card hover:scale-105 text-tx-secondary"
                      }`}
                    >
                      <span
                        className="h-4 w-4 shrink-0 rounded-full"
                        style={{ backgroundColor: preset.swatch }}
                      />
                      {preset.name}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-tx-muted mb-0.5">
                  Active: <span className="font-medium text-tx-secondary">
                    {THEME_PRESETS.find(p => p.id === activePreset)?.name ?? "Default"}
                  </span>
                </p>

                <div className="my-2 border-t border-border-subtle" />

                {/* Background section — dimmed when a theme preset overrides */}
                <div className={isPresetActive ? "opacity-40 pointer-events-none" : ""}>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-tx-muted">Background</p>
                  <div className="flex gap-1.5 mb-3">
                    {BG_PALETTES.map((p, i) => (
                      <button
                        key={p.name}
                        onClick={() => {
                          setActiveBg(i);
                          localStorage.setItem("sherpa-bg-palette", String(i));
                          if (i === 0) clearBgPalette();
                          else applyBgPalette(p);
                        }}
                        title={p.name}
                        className={`h-8 w-8 shrink-0 rounded-lg border-2 shadow-sm transition ${
                          activeBg === i ? "border-white ring-2 ring-primary scale-110" : "border-transparent hover:scale-105"
                        }`}
                        style={{ background: `linear-gradient(135deg, ${p.surface} 50%, ${p.surfaceAlt} 50%)` }}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] text-tx-muted mb-0.5">
                    Active: <span className="font-medium text-tx-secondary">{BG_PALETTES[activeBg]?.name}</span>
                  </p>
                </div>

                <div className="my-2 border-t border-border-subtle" />

                {/* Accent section — dimmed when a theme preset overrides */}
                <div className={isPresetActive ? "opacity-40 pointer-events-none" : ""}>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-tx-muted">Accent</p>
                  <div className="flex gap-1.5 mb-3">
                    {ACCENT_PALETTES.map((p, i) => (
                      <button
                        key={p.name}
                        onClick={() => {
                          setActiveAccent(i);
                          localStorage.setItem("sherpa-accent-palette", String(i));
                          if (i === 0) clearAccentPalette();
                          else applyAccentPalette(p);
                        }}
                        title={p.name}
                        className={`h-8 w-8 shrink-0 rounded-full border-2 shadow-sm transition ${
                          activeAccent === i ? "border-white ring-2 ring-offset-1 ring-offset-card scale-110" : "border-transparent hover:scale-105"
                        }`}
                        style={{ backgroundColor: p.swatch }}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] text-tx-muted">
                    Active: <span className="font-medium text-tx-secondary">{ACCENT_PALETTES[activeAccent]?.name}</span>
                  </p>
                </div>
              </div>
            )}
          </div>

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
            <Outlet context={{ setEditorBreadcrumb } as AppShellContext} />
          </div>
        </main>

        {/* Status bar */}
        <footer className="flex h-6 shrink-0 items-center justify-between border-t border-nav-border bg-nav px-4 text-xs text-tx-muted">
          <div className="flex items-center gap-4">
            <span>TTS Tax Prep v{CLIENT_VERSION}</span>
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

      {/* ── AI Help Panel ── */}
      <AiHelpPanel />

      {/* ── About Dialog ── */}
      {showAbout && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={() => setShowAbout(false)}>
          <div className="w-[380px] rounded-xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 text-center">
              <h2 className="text-xl font-bold text-primary">TTS Tax Prep</h2>
              <p className="mt-1 text-sm text-tx-secondary">Professional Tax Preparation Software</p>
            </div>

            <div className="space-y-2 rounded-lg bg-surface p-4">
              <div className="flex justify-between text-sm">
                <span className="text-tx-secondary">Client version</span>
                <span className="font-semibold text-tx">v{CLIENT_VERSION}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-tx-secondary">Server version</span>
                <span className="font-semibold text-tx">
                  {serverVersion === null ? (
                    <span className="text-tx-muted">loading...</span>
                  ) : serverVersion === "unavailable" ? (
                    <span className="text-tx-muted">unavailable</span>
                  ) : (
                    `v${serverVersion}`
                  )}
                </span>
              </div>
              {serverVersion && serverVersion !== "unavailable" && serverVersion !== CLIENT_VERSION && (
                <div className="mt-1 rounded bg-amber-50 px-2 py-1 text-xs text-amber-700">
                  Version mismatch detected
                </div>
              )}
            </div>

            <div className="mt-4 text-center">
              <p className="text-xs text-tx-muted">The Tax Shelter</p>
            </div>

            <div className="mt-4 flex justify-center">
              <button
                onClick={() => setShowAbout(false)}
                className="rounded-lg bg-primary px-6 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-hover"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
