import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";

import "./index.css";
import { AuthProvider, useAuth } from "./lib/auth";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ClientDetail from "./pages/ClientDetail";
import EntityDetail from "./pages/EntityDetail";
import TrialBalance from "./pages/TrialBalance";
import FormEditor from "./pages/FormEditor";

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">Loading...</p>
      </div>
    );
  }

  if (!user) return <Login />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        {/* Client Manager (home) */}
        <Route path="/" element={<Dashboard />} />

        {/* Entity Manager for a client */}
        <Route path="/clients/:clientId" element={<ClientDetail />} />

        {/* Entity Detail — tax years, TB, returns */}
        <Route path="/clients/:clientId/entities/:entityId" element={<EntityDetail />} />

        {/* Trial Balance & Form Editor */}
        <Route path="/tax-years/:taxYearId/trial-balance" element={<TrialBalance />} />
        <Route path="/tax-returns/:taxReturnId/editor" element={<FormEditor />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </HashRouter>
  </StrictMode>
);
