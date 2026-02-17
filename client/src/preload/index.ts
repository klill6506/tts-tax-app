import { contextBridge, ipcRenderer, webUtils } from "electron";

/**
 * Expose a safe `window.api` object to the renderer process.
 * All Django communication goes through IPC → main process.
 */
contextBridge.exposeInMainWorld("api", {
  request: (method: string, path: string, body?: unknown) =>
    ipcRenderer.invoke("api:request", { method, path, body }),
  uploadFile: (
    path: string,
    fields: Record<string, string>,
    fileFieldName: string,
    filePath: string,
    fileName: string
  ) =>
    ipcRenderer.invoke("api:uploadFile", {
      path,
      fields,
      fileFieldName,
      filePath,
      fileName,
    }),
  getFilePath: (file: File) => webUtils.getPathForFile(file),
  renderPdf: (taxReturnId: string) =>
    ipcRenderer.invoke("api:renderPdf", taxReturnId),
  renderK1s: (taxReturnId: string) =>
    ipcRenderer.invoke("api:renderK1s", taxReturnId),
  renderK1: (taxReturnId: string, shareholderId: string) =>
    ipcRenderer.invoke("api:renderK1", taxReturnId, shareholderId),
  render7206: (taxReturnId: string, shareholderId: string) =>
    ipcRenderer.invoke("api:render7206", taxReturnId, shareholderId),
  clearSession: () => ipcRenderer.invoke("api:clearSession"),
});
