import { app, BrowserWindow, ipcMain, net } from "electron";
import fs from "fs";
import http from "http";
import path from "path";

const API_BASE = "http://127.0.0.1:8000/api/v1";

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "TTS Tax Prep",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // In dev, load from Vite dev server; in prod, load built files
  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  app.quit();
});

// ---------------------------------------------------------------------------
// IPC → Django API bridge
// All API calls go through the main process (per client/CLAUDE.md).
// The renderer sends { method, path, body } and gets back { ok, status, data }.
// ---------------------------------------------------------------------------

interface ApiRequest {
  method: string;
  path: string;
  body?: unknown;
}

interface ApiResponse {
  ok: boolean;
  status: number;
  data: unknown;
}

// Store session cookie from Django
let sessionCookie = "";

ipcMain.handle(
  "api:request",
  async (_event, req: ApiRequest): Promise<ApiResponse> => {
    const url = `${API_BASE}${req.path}`;
    const method = (req.method || "GET").toUpperCase();

    return new Promise((resolve) => {
      const request = net.request({ url, method });

      // Send session cookie if we have one
      if (sessionCookie) {
        request.setHeader("Cookie", sessionCookie);
      }

      // Set content type and CSRF token for POST/PATCH/PUT/DELETE
      if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
        if (req.body) {
          request.setHeader("Content-Type", "application/json");
        }
        // Extract csrftoken from stored cookies and send as header
        const csrfMatch = sessionCookie.match(/csrftoken=([^;]+)/);
        if (csrfMatch) {
          request.setHeader("X-CSRFToken", csrfMatch[1]);
        }
      }

      let responseData = "";
      let statusCode = 0;

      request.on("response", (response) => {
        statusCode = response.statusCode;

        // Capture Set-Cookie headers for session management
        const cookies = response.headers["set-cookie"];
        if (cookies) {
          const cookieArray = Array.isArray(cookies) ? cookies : [cookies];
          for (const cookie of cookieArray) {
            if (cookie.startsWith("sessionid=") || cookie.startsWith("csrftoken=")) {
              // Update our stored cookies
              const name = cookie.split("=")[0];
              const fullCookie = cookie.split(";")[0];
              if (sessionCookie) {
                // Replace existing cookie or append
                const re = new RegExp(`${name}=[^;]*`);
                if (re.test(sessionCookie)) {
                  sessionCookie = sessionCookie.replace(re, fullCookie);
                } else {
                  sessionCookie += `; ${fullCookie}`;
                }
              } else {
                sessionCookie = fullCookie;
              }
            }
          }
        }

        response.on("data", (chunk) => {
          responseData += chunk.toString();
        });

        response.on("end", () => {
          let parsed: unknown;
          try {
            parsed = JSON.parse(responseData);
          } catch {
            parsed = responseData;
          }
          resolve({ ok: statusCode >= 200 && statusCode < 300, status: statusCode, data: parsed });
        });
      });

      request.on("error", (error) => {
        resolve({ ok: false, status: 0, data: { error: error.message } });
      });

      if (req.body && ["POST", "PATCH", "PUT"].includes(method)) {
        request.write(JSON.stringify(req.body));
      }
      request.end();
    });
  }
);

// ---------------------------------------------------------------------------
// File upload IPC handler (multipart/form-data)
// Reads file from disk (via path) to avoid IPC binary serialization issues.
// ---------------------------------------------------------------------------

interface FileUploadRequest {
  path: string;
  fields: Record<string, string>;
  fileFieldName: string;
  filePath: string; // absolute path on disk
  fileName: string;
}

ipcMain.handle(
  "api:uploadFile",
  async (_event, req: FileUploadRequest): Promise<ApiResponse> => {
    const boundary = `----ElectronBoundary${Date.now()}`;

    // Read file from disk in the main process
    let fileBuffer: Buffer;
    try {
      fileBuffer = fs.readFileSync(req.filePath);
    } catch (err) {
      return { ok: false, status: 0, data: { error: `Cannot read file: ${(err as Error).message}` } };
    }

    // Build multipart body
    const parts: Buffer[] = [];

    for (const [key, value] of Object.entries(req.fields)) {
      parts.push(
        Buffer.from(
          `--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${value}\r\n`
        )
      );
    }

    parts.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="${req.fileFieldName}"; filename="${req.fileName}"\r\nContent-Type: application/octet-stream\r\n\r\n`
      )
    );
    parts.push(fileBuffer);
    parts.push(Buffer.from("\r\n"));
    parts.push(Buffer.from(`--${boundary}--\r\n`));

    const body = Buffer.concat(parts);

    // Use Node http module (Electron net.request has issues with binary writes)
    const headers: Record<string, string> = {
      "Content-Type": `multipart/form-data; boundary=${boundary}`,
      "Content-Length": String(body.length),
    };
    if (sessionCookie) {
      headers["Cookie"] = sessionCookie;
    }
    const csrfMatch = sessionCookie.match(/csrftoken=([^;]+)/);
    if (csrfMatch) {
      headers["X-CSRFToken"] = csrfMatch[1];
    }

    return new Promise((resolve) => {
      const request = http.request(
        `http://127.0.0.1:8000/api/v1${req.path}`,
        { method: "POST", headers },
        (response) => {
          let responseData = "";

          // Capture Set-Cookie for session management
          const cookies = response.headers["set-cookie"];
          if (cookies) {
            for (const cookie of cookies) {
              if (cookie.startsWith("sessionid=") || cookie.startsWith("csrftoken=")) {
                const name = cookie.split("=")[0];
                const fullCookie = cookie.split(";")[0];
                if (sessionCookie) {
                  const re = new RegExp(`${name}=[^;]*`);
                  if (re.test(sessionCookie)) {
                    sessionCookie = sessionCookie.replace(re, fullCookie);
                  } else {
                    sessionCookie += `; ${fullCookie}`;
                  }
                } else {
                  sessionCookie = fullCookie;
                }
              }
            }
          }

          response.on("data", (chunk) => {
            responseData += chunk.toString();
          });

          response.on("end", () => {
            const statusCode = response.statusCode || 0;
            let parsed: unknown;
            try {
              parsed = JSON.parse(responseData);
            } catch {
              parsed = responseData;
            }
            resolve({ ok: statusCode >= 200 && statusCode < 300, status: statusCode, data: parsed });
          });
        }
      );

      request.on("error", (error) => {
        resolve({ ok: false, status: 0, data: { error: error.message } });
      });

      request.write(body);
      request.end();
    });
  }
);

// ---------------------------------------------------------------------------
// PDF render IPC handler (binary response via base64)
// Uses Node http module and collects response as Buffer to preserve binary data.
// ---------------------------------------------------------------------------

ipcMain.handle(
  "api:renderPdf",
  async (_event, taxReturnId: string): Promise<{ ok: boolean; pdfBase64?: string; error?: string }> => {
    const headers: Record<string, string> = {
      "Content-Length": "0",
    };
    if (sessionCookie) {
      headers["Cookie"] = sessionCookie;
    }
    const csrfMatch = sessionCookie.match(/csrftoken=([^;]+)/);
    if (csrfMatch) {
      headers["X-CSRFToken"] = csrfMatch[1];
    }

    return new Promise((resolve) => {
      const request = http.request(
        `http://127.0.0.1:8000/api/v1/tax-returns/${taxReturnId}/render-pdf/`,
        { method: "POST", headers },
        (response) => {
          const chunks: Buffer[] = [];

          // Capture Set-Cookie for session management
          const cookies = response.headers["set-cookie"];
          if (cookies) {
            for (const cookie of cookies) {
              if (cookie.startsWith("sessionid=") || cookie.startsWith("csrftoken=")) {
                const name = cookie.split("=")[0];
                const fullCookie = cookie.split(";")[0];
                if (sessionCookie) {
                  const re = new RegExp(`${name}=[^;]*`);
                  if (re.test(sessionCookie)) {
                    sessionCookie = sessionCookie.replace(re, fullCookie);
                  } else {
                    sessionCookie += `; ${fullCookie}`;
                  }
                } else {
                  sessionCookie = fullCookie;
                }
              }
            }
          }

          response.on("data", (chunk: Buffer) => {
            chunks.push(chunk);
          });

          response.on("end", () => {
            const statusCode = response.statusCode || 0;
            if (statusCode >= 200 && statusCode < 300) {
              const pdfBuffer = Buffer.concat(chunks);
              resolve({ ok: true, pdfBase64: pdfBuffer.toString("base64") });
            } else {
              const body = Buffer.concat(chunks).toString("utf-8");
              let errorMsg = `Server returned ${statusCode}`;
              try {
                const parsed = JSON.parse(body);
                if (parsed.error) errorMsg = parsed.error;
              } catch { /* use default */ }
              resolve({ ok: false, error: errorMsg });
            }
          });
        }
      );

      request.on("error", (error) => {
        resolve({ ok: false, error: error.message });
      });

      request.end();
    });
  }
);

// ---------------------------------------------------------------------------
// PDF render helpers for K-1s and Form 7206
// Same pattern as api:renderPdf but with different endpoints.
// ---------------------------------------------------------------------------

function renderPdfFromEndpoint(
  urlPath: string
): Promise<{ ok: boolean; pdfBase64?: string; error?: string }> {
  const headers: Record<string, string> = {
    "Content-Length": "0",
  };
  if (sessionCookie) {
    headers["Cookie"] = sessionCookie;
  }
  const csrfMatch = sessionCookie.match(/csrftoken=([^;]+)/);
  if (csrfMatch) {
    headers["X-CSRFToken"] = csrfMatch[1];
  }

  return new Promise((resolve) => {
    const request = http.request(
      `http://127.0.0.1:8000/api/v1${urlPath}`,
      { method: "POST", headers },
      (response) => {
        const chunks: Buffer[] = [];

        const cookies = response.headers["set-cookie"];
        if (cookies) {
          for (const cookie of cookies) {
            if (cookie.startsWith("sessionid=") || cookie.startsWith("csrftoken=")) {
              const name = cookie.split("=")[0];
              const fullCookie = cookie.split(";")[0];
              if (sessionCookie) {
                const re = new RegExp(`${name}=[^;]*`);
                if (re.test(sessionCookie)) {
                  sessionCookie = sessionCookie.replace(re, fullCookie);
                } else {
                  sessionCookie += `; ${fullCookie}`;
                }
              } else {
                sessionCookie = fullCookie;
              }
            }
          }
        }

        response.on("data", (chunk: Buffer) => {
          chunks.push(chunk);
        });

        response.on("end", () => {
          const statusCode = response.statusCode || 0;
          if (statusCode >= 200 && statusCode < 300) {
            const pdfBuffer = Buffer.concat(chunks);
            resolve({ ok: true, pdfBase64: pdfBuffer.toString("base64") });
          } else {
            const body = Buffer.concat(chunks).toString("utf-8");
            let errorMsg = `Server returned ${statusCode}`;
            try {
              const parsed = JSON.parse(body);
              if (parsed.error) errorMsg = parsed.error;
            } catch { /* use default */ }
            resolve({ ok: false, error: errorMsg });
          }
        });
      }
    );

    request.on("error", (error) => {
      resolve({ ok: false, error: error.message });
    });

    request.end();
  });
}

ipcMain.handle(
  "api:renderK1s",
  async (_event, taxReturnId: string) => {
    return renderPdfFromEndpoint(`/tax-returns/${taxReturnId}/render-k1s/`);
  }
);

ipcMain.handle(
  "api:renderK1",
  async (_event, taxReturnId: string, shareholderId: string) => {
    return renderPdfFromEndpoint(`/tax-returns/${taxReturnId}/render-k1/${shareholderId}/`);
  }
);

ipcMain.handle(
  "api:render7206",
  async (_event, taxReturnId: string, shareholderId: string) => {
    return renderPdfFromEndpoint(`/tax-returns/${taxReturnId}/render-7206/${shareholderId}/`);
  }
);

// Clear session on logout
ipcMain.handle("api:clearSession", async () => {
  sessionCookie = "";
  return { ok: true };
});
