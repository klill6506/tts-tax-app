import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";

import "./index.css";
import { AuthProvider, useAuth } from "./lib/auth";
import { FormContextProvider } from "./lib/form-context";
import { ThemeProvider } from "./lib/theme";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import ClientReturns from "./pages/ClientReturns";
import EntityDetail from "./pages/EntityDetail";
import TrialBalance from "./pages/TrialBalance";
import FormEditor from "./pages/FormEditor";
import FormPreview from "./pages/FormPreview";
import ReturnManager from "./pages/ReturnManager";
import PreparerManager from "./pages/PreparerManager";
import PrintPackageManager from "./pages/PrintPackageManager";
import ClientFolders from "./pages/ClientFolders";
import FolderDetail from "./pages/FolderDetail";

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
        {/* Return Manager (home) */}
        <Route path="/" element={<ReturnManager />} />
        <Route path="/returns" element={<ReturnManager />} />

        {/* Client Returns — all returns for an individual */}
        <Route path="/clients/:clientId" element={<ClientReturns />} />

        {/* Entity Detail — tax years, TB, returns */}
        <Route path="/clients/:clientId/entities/:entityId" element={<EntityDetail />} />

        {/* Client Folders (document management) */}
        <Route path="/folders" element={<ClientFolders />} />
        <Route path="/folders/:entityId" element={<FolderDetail />} />

        {/* Admin */}
        <Route path="/admin/preparers" element={<PreparerManager />} />
        <Route path="/admin/print-packages" element={<PrintPackageManager />} />

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
          <FormContextProvider>
            <AppRoutes />
          </FormContextProvider>
        </AuthProvider>
      </HashRouter>
    </ThemeProvider>
  </StrictMode>
);
