/**
 * Universal API adapter — works in both Electron (IPC bridge) and web (fetch).
 *
 * Detection: if `window.api` exists, we're in Electron and use the IPC bridge.
 * Otherwise we use native fetch() against the same origin.
 */

const API_BASE = "/api/v1";

function isElectron(): boolean {
  return typeof window !== "undefined" && !!window.api;
}

// ---------------------------------------------------------------------------
// CSRF helper (web only — reads Django's csrftoken cookie)
// ---------------------------------------------------------------------------

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(^| )csrftoken=([^;]+)/);
  return match ? match[2] : null;
}

// ---------------------------------------------------------------------------
// Core JSON API
// ---------------------------------------------------------------------------

export async function api(
  method: string,
  path: string,
  body?: unknown
): Promise<{ ok: boolean; status: number; data: unknown }> {
  if (isElectron()) {
    return window.api!.request(method, path, body);
  }

  const headers: Record<string, string> = {};
  if (body) headers["Content-Type"] = "application/json";
  if (["POST", "PATCH", "PUT", "DELETE"].includes(method.toUpperCase())) {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });

  let data: unknown;
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    data = await resp.json();
  } else {
    data = await resp.text();
  }

  return { ok: resp.ok, status: resp.status, data };
}

export async function get(path: string) {
  return api("GET", path);
}

export async function post(path: string, body?: unknown) {
  return api("POST", path, body);
}

export async function patch(path: string, body?: unknown) {
  return api("PATCH", path, body);
}

export async function del(path: string) {
  return api("DELETE", path);
}

// ---------------------------------------------------------------------------
// File upload
// ---------------------------------------------------------------------------

export async function uploadFile(
  path: string,
  fields: Record<string, string>,
  file: File
): Promise<{ ok: boolean; status: number; data: unknown }> {
  if (isElectron()) {
    const filePath = window.api!.getFilePath(file);
    return window.api!.uploadFile(path, fields, "file", filePath, file.name);
  }

  // Web: standard FormData
  const formData = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    formData.append(key, value);
  }
  formData.append("file", file);

  const headers: Record<string, string> = {};
  const csrf = getCsrfToken();
  if (csrf) headers["X-CSRFToken"] = csrf;

  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });

  let data: unknown;
  try {
    data = await resp.json();
  } catch {
    data = await resp.text();
  }
  return { ok: resp.ok, status: resp.status, data };
}

// ---------------------------------------------------------------------------
// PDF rendering helpers
// ---------------------------------------------------------------------------

interface PdfResponse {
  ok: boolean;
  pdfBase64?: string;
  error?: string;
}

async function fetchPdf(urlPath: string): Promise<PdfResponse> {
  const headers: Record<string, string> = {};
  const csrf = getCsrfToken();
  if (csrf) headers["X-CSRFToken"] = csrf;

  try {
    const resp = await fetch(`${API_BASE}${urlPath}`, {
      method: "POST",
      headers,
      credentials: "include",
    });

    if (resp.ok) {
      const buffer = await resp.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return { ok: true, pdfBase64: btoa(binary) };
    }

    let errorMsg = `Server returned ${resp.status}`;
    try {
      const parsed = await resp.json();
      if (parsed.error) errorMsg = parsed.error;
    } catch {
      // non-JSON error response
    }
    return { ok: false, error: errorMsg };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export async function renderPdf(taxReturnId: string): Promise<PdfResponse> {
  if (isElectron()) return window.api!.renderPdf(taxReturnId);
  return fetchPdf(`/tax-returns/${taxReturnId}/render-pdf/`);
}

export async function renderK1s(taxReturnId: string): Promise<PdfResponse> {
  if (isElectron()) return window.api!.renderK1s(taxReturnId);
  return fetchPdf(`/tax-returns/${taxReturnId}/render-k1s/`);
}

export async function renderK1(
  taxReturnId: string,
  shareholderId: string
): Promise<PdfResponse> {
  if (isElectron()) return window.api!.renderK1(taxReturnId, shareholderId);
  return fetchPdf(
    `/tax-returns/${taxReturnId}/render-k1/${shareholderId}/`
  );
}

export async function render7206(
  taxReturnId: string,
  shareholderId: string
): Promise<PdfResponse> {
  if (isElectron()) return window.api!.render7206(taxReturnId, shareholderId);
  return fetchPdf(
    `/tax-returns/${taxReturnId}/render-7206/${shareholderId}/`
  );
}

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------

export async function clearSession(): Promise<void> {
  if (isElectron()) {
    await window.api!.clearSession();
  }
  // In web mode, Django's logout endpoint already clears the session cookie.
}
