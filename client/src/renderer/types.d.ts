/** Types exposed by the preload script on window.api */

interface ApiResponse {
  ok: boolean;
  status: number;
  data: unknown;
}

interface ElectronApi {
  request: (method: string, path: string, body?: unknown) => Promise<ApiResponse>;
  clearSession: () => Promise<{ ok: boolean }>;
}

declare global {
  interface Window {
    api: ElectronApi;
  }
}

export {};
