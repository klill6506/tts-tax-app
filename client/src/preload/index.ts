import { contextBridge, ipcRenderer } from "electron";

/**
 * Expose a safe `window.api` object to the renderer process.
 * All Django communication goes through IPC → main process.
 */
contextBridge.exposeInMainWorld("api", {
  request: (method: string, path: string, body?: unknown) =>
    ipcRenderer.invoke("api:request", { method, path, body }),
  clearSession: () => ipcRenderer.invoke("api:clearSession"),
});
