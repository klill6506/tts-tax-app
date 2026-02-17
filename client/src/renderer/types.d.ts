/** Types exposed by the preload script on window.api */

interface ApiResponse {
  ok: boolean;
  status: number;
  data: unknown;
}

interface PdfResponse {
  ok: boolean;
  pdfBase64?: string;
  error?: string;
}

interface ElectronApi {
  request: (method: string, path: string, body?: unknown) => Promise<ApiResponse>;
  uploadFile: (
    path: string,
    fields: Record<string, string>,
    fileFieldName: string,
    filePath: string,
    fileName: string
  ) => Promise<ApiResponse>;
  getFilePath: (file: File) => string;
  renderPdf: (taxReturnId: string) => Promise<PdfResponse>;
  renderK1s: (taxReturnId: string) => Promise<PdfResponse>;
  renderK1: (taxReturnId: string, shareholderId: string) => Promise<PdfResponse>;
  render7206: (taxReturnId: string, shareholderId: string) => Promise<PdfResponse>;
  clearSession: () => Promise<{ ok: boolean }>;
}

declare global {
  interface Window {
    api: ElectronApi;
  }
}

export {};
