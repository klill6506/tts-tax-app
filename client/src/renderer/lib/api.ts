/**
 * API adapter — standard fetch() against the same origin (Django).
 */

const API_BASE = "/api/v1";

// ---------------------------------------------------------------------------
// CSRF helper (reads Django's csrftoken cookie)
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
  return fetchPdf(`/tax-returns/${taxReturnId}/render-pdf/`);
}

export async function renderK1s(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-k1s/`);
}

export async function renderK1(
  taxReturnId: string,
  shareholderId: string
): Promise<PdfResponse> {
  return fetchPdf(
    `/tax-returns/${taxReturnId}/render-k1/${shareholderId}/`
  );
}

export async function render7206(
  taxReturnId: string,
  shareholderId: string
): Promise<PdfResponse> {
  return fetchPdf(
    `/tax-returns/${taxReturnId}/render-7206/${shareholderId}/`
  );
}

export async function render1125a(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-1125a/`);
}

export async function render8825(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-8825/`);
}

export async function render7203(
  taxReturnId: string,
  shareholderId: string
): Promise<PdfResponse> {
  return fetchPdf(
    `/tax-returns/${taxReturnId}/render-7203/${shareholderId}/`
  );
}

export async function render7203s(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-7203s/`);
}

export async function render7004(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-7004/`);
}

export async function renderComplete(
  taxReturnId: string,
  packageName?: string
): Promise<PdfResponse> {
  const qs = packageName ? `?package=${packageName}` : "";
  return fetchPdf(`/tax-returns/${taxReturnId}/render-complete/${qs}`);
}

export async function renderInvoice(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-invoice/`);
}

export async function renderLetter(taxReturnId: string): Promise<PdfResponse> {
  return fetchPdf(`/tax-returns/${taxReturnId}/render-letter/`);
}

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------

export async function clearSession(): Promise<void> {
  // Django's logout endpoint clears the session cookie.
}
