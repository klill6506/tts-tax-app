import { app, BrowserWindow, ipcMain, net } from "electron";
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

// Clear session on logout
ipcMain.handle("api:clearSession", async () => {
  sessionCookie = "";
  return { ok: true };
});
