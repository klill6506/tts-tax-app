import { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { ReactNode } from "react";

type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  cycle: () => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

const STORAGE_KEY = "tts-theme";
const CYCLE_ORDER: ThemeMode[] = ["light", "dark", "system"];

function getSystemPreference(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function resolve(mode: ThemeMode): "light" | "dark" {
  return mode === "system" ? getSystemPreference() : mode;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
    return stored && CYCLE_ORDER.includes(stored) ? stored : "light";
  });

  const resolved = resolve(mode);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    localStorage.setItem(STORAGE_KEY, m);
  }, []);

  const cycle = useCallback(() => {
    const idx = CYCLE_ORDER.indexOf(mode);
    const next = CYCLE_ORDER[(idx + 1) % CYCLE_ORDER.length];
    setMode(next);
  }, [mode, setMode]);

  // Apply .dark class to <html>
  useEffect(() => {
    const el = document.documentElement;
    if (resolved === "dark") {
      el.classList.add("dark");
    } else {
      el.classList.remove("dark");
    }
  }, [resolved]);

  // Listen for system preference changes when mode is "system"
  useEffect(() => {
    if (mode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setModeState((prev) => (prev === "system" ? "system" : prev));
    // Force re-render when system preference changes
    const forceUpdate = () => {
      setModeState("system");
    };
    mq.addEventListener("change", forceUpdate);
    return () => mq.removeEventListener("change", forceUpdate);
  }, [mode]);

  return (
    <ThemeContext.Provider value={{ mode, resolved, setMode, cycle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
