import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { renderPdf } from "../lib/api";

export default function FormPreview() {
  const { taxReturnId } = useParams<{ taxReturnId: string }>();
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!taxReturnId) return;

    renderPdf(taxReturnId).then((res) => {
      if (res.ok && res.pdfBase64) {
        // Decode base64 → binary → Blob → object URL
        const binary = atob(res.pdfBase64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        setPdfUrl(url);
      } else {
        setError(res.error || "Failed to generate PDF.");
      }
      setLoading(false);
    });

    return () => {
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
      }
    };
  }, [taxReturnId]);

  function handleDownload() {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `tax-return-${taxReturnId}.pdf`;
    a.click();
  }

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-primary-subtle border-t-primary" />
          <p className="text-sm text-tx-secondary">Generating IRS form PDF...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center">
        <p className="mb-4 text-sm text-danger">{error}</p>
        <Link
          to={`/tax-returns/${taxReturnId}/editor`}
          className="text-sm font-medium text-primary-text hover:underline"
        >
          Back to Editor
        </Link>
      </div>
    );
  }

  return (
    <div className="-m-6 flex flex-col" style={{ height: "calc(100vh - 6.5rem)" }}>
      {/* Toolbar */}
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-card px-4 py-2">
        <Link
          to={`/tax-returns/${taxReturnId}/editor`}
          className="inline-flex items-center gap-1 text-sm font-medium text-primary-text hover:underline"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back to Editor
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
          >
            Download PDF
          </button>
        </div>
      </div>

      {/* PDF Viewer */}
      {pdfUrl && (
        <iframe
          src={pdfUrl}
          className="min-h-0 flex-1 border-0"
          title="IRS Form Preview"
        />
      )}
    </div>
  );
}
