import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";

import "./index.css";
import { AuthProvider, useAuth } from "./lib/auth";
import { ThemeProvider } from "./lib/theme";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ClientDetail from "./pages/ClientDetail";
import EntityDetail from "./pages/EntityDetail";
import TrialBalance from "./pages/TrialBalance";
import FormEditor from "./pages/FormEditor";
import FormPreview from "./pages/FormPreview";
import ReturnManager from "./pages/ReturnManager";

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <p className="text-sm text-tx-muted">Loading...</p>
      </div>
    );
  }

  if (!user) return <Login />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        {/* Client Manager (home) */}
        <Route path="/" element={<Dashboard />} />

        {/* Return Manager */}
        <Route path="/returns" element={<ReturnManager />} />

        {/* Entity Manager for a client */}
        <Route path="/clients/:clientId" element={<ClientDetail />} />

        {/* Entity Detail — tax years, TB, returns */}
        <Route path="/clients/:clientId/entities/:entityId" element={<EntityDetail />} />

        {/* Trial Balance & Form Editor */}
        <Route path="/tax-years/:taxYearId/trial-balance" element={<TrialBalance />} />
        <Route path="/tax-returns/:taxReturnId/editor" element={<FormEditor />} />
        <Route path="/tax-returns/:taxReturnId/preview" element={<FormPreview />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <HashRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </HashRouter>
    </ThemeProvider>
  </StrictMode>
);
