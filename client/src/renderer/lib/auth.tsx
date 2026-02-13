import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { ReactNode } from "react";
import { post, get } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Membership {
  firm_id: string;
  firm_name: string;
  role: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  memberships: Membership[];
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount, try to restore session via /me/
  // In dev mode, auto-login if no active session
  useEffect(() => {
    async function init() {
      const res = await get("/me/");
      if (res.ok) {
        const payload = res.data as { data: User };
        setUser(payload.data);
      } else if (
        import.meta.env.DEV &&
        import.meta.env.VITE_DEV_USER &&
        import.meta.env.VITE_DEV_PASS
      ) {
        // Auto-login in dev mode using .env.local credentials
        const loginRes = await post("/auth/login/", {
          username: import.meta.env.VITE_DEV_USER,
          password: import.meta.env.VITE_DEV_PASS,
        });
        if (loginRes.ok) {
          const payload = loginRes.data as { data: User };
          setUser(payload.data);
        }
      }
      setLoading(false);
    }
    init();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await post("/auth/login/", { username, password });
    if (res.ok) {
      const payload = res.data as { data: User };
      setUser(payload.data);
      return null; // success
    }
    const err = res.data as { error?: string };
    return err.error || "Login failed.";
  }, []);

  const logout = useCallback(async () => {
    await post("/auth/logout/");
    await window.api.clearSession();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
