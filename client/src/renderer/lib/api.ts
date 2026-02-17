/**
 * Thin wrapper around the IPC bridge for cleaner call sites.
 */

export async function api(method: string, path: string, body?: unknown) {
  return window.api.request(method, path, body);
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

export async function uploadFile(
  path: string,
  fields: Record<string, string>,
  file: File
) {
  // Electron 29+ requires webUtils.getPathForFile() to get the disk path
  const filePath = window.api.getFilePath(file);
  return window.api.uploadFile(path, fields, "file", filePath, file.name);
}
