/**
 * PDF.js-based PDF viewer with continuous scroll and custom toolbar.
 *
 * Renders all pages to canvas elements with proper dimensions.
 * Simpler and more reliable than virtual rendering for typical
 * tax return PDFs (20-40 pages).
 */

import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface PdfViewerProps {
  /** PDF data as Uint8Array or ArrayBuffer */
  data: Uint8Array | ArrayBuffer | null;
  /** Callback when the visible page changes (1-indexed) */
  onPageChange?: (page: number) => void;
  /** Imperatively scroll to this page (1-indexed). Changes trigger scroll. */
  goToPage?: number;
}

const SCALE_STEP = 0.15;
const MIN_SCALE = 0.5;
const MAX_SCALE = 3.0;
const PAGE_GAP = 8;

export default function PdfViewer({ data, onPageChange, goToPage }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  // Load PDF document
  useEffect(() => {
    if (!data) {
      setPdf(null);
      setNumPages(0);
      setRendered(false);
      return;
    }

    setLoading(true);
    setError(null);
    setRendered(false);

    const loadingTask = pdfjsLib.getDocument({ data });
    loadingTask.promise
      .then((doc) => {
        setPdf(doc);
        setNumPages(doc.numPages);
        setCurrentPage(1);
        setLoading(false);
      })
      .catch((err) => {
        setError(`Failed to load PDF: ${err.message}`);
        setLoading(false);
      });

    return () => {
      loadingTask.destroy();
    };
  }, [data]);

  // Compute fit-to-width scale and render all pages
  useEffect(() => {
    if (!pdf || !containerRef.current) return;
    let cancelled = false;

    async function renderAll() {
      const firstPage = await pdf!.getPage(1);
      const baseViewport = firstPage.getViewport({ scale: 1 });
      const containerWidth = containerRef.current!.clientWidth - 32;
      const fitScale = containerWidth / baseViewport.width;
      if (cancelled) return;
      setScale(fitScale);

      const dpr = window.devicePixelRatio || 1;

      for (let i = 1; i <= pdf!.numPages; i++) {
        if (cancelled) return;
        const page = await pdf!.getPage(i);
        const viewport = page.getViewport({ scale: fitScale });

        const wrapper = pageRefs.current.get(i);
        if (!wrapper) continue;

        // Create canvas for this page
        let canvas = wrapper.querySelector("canvas");
        if (!canvas) {
          canvas = document.createElement("canvas");
          wrapper.appendChild(canvas);
        }

        // Set canvas pixel dimensions (high-DPI)
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        // Set CSS display dimensions
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        // Set wrapper dimensions to match
        wrapper.style.width = `${Math.floor(viewport.width)}px`;
        wrapper.style.height = `${Math.floor(viewport.height)}px`;

        const ctx = canvas.getContext("2d")!;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        await page.render({ canvasContext: ctx, viewport }).promise;
      }

      if (!cancelled) setRendered(true);
    }

    renderAll();
    return () => { cancelled = true; };
  }, [pdf]);

  // Track scroll position to update current page
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !rendered) return;

    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const scrollCenter = container!.scrollTop + container!.clientHeight / 3;
        let accHeight = 0;
        let page = 1;
        for (const [pageNum, wrapper] of pageRefs.current) {
          const h = wrapper.offsetHeight + PAGE_GAP;
          if (accHeight + h > scrollCenter) {
            page = pageNum;
            break;
          }
          accHeight += h;
        }
        if (page !== currentPage) {
          setCurrentPage(page);
          onPageChange?.(page);
        }
      });
    }

    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, [rendered, currentPage, onPageChange]);

  // Handle goToPage
  useEffect(() => {
    if (!goToPage || !rendered) return;
    const wrapper = pageRefs.current.get(goToPage);
    if (wrapper) {
      wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [goToPage, rendered]);

  // Zoom (re-render at new scale)
  async function rerender(newScale: number) {
    if (!pdf) return;
    setScale(newScale);
    const dpr = window.devicePixelRatio || 1;

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: newScale });
      const wrapper = pageRefs.current.get(i);
      if (!wrapper) continue;
      const canvas = wrapper.querySelector("canvas");
      if (!canvas) continue;

      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;
      wrapper.style.width = `${Math.floor(viewport.width)}px`;
      wrapper.style.height = `${Math.floor(viewport.height)}px`;

      const ctx = canvas.getContext("2d")!;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      await page.render({ canvasContext: ctx, viewport }).promise;
    }
  }

  function zoomIn() { rerender(Math.min(scale + SCALE_STEP, MAX_SCALE)); }
  function zoomOut() { rerender(Math.max(scale - SCALE_STEP, MIN_SCALE)); }

  function handleDownload() {
    if (!data) return;
    const blob = new Blob([data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tax_return.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handlePrint() {
    if (!data) return;
    const blob = new Blob([data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const w = window.open(url);
    if (w) w.addEventListener("load", () => w.print());
  }

  function scrollToPage(page: number) {
    const wrapper = pageRefs.current.get(page);
    if (wrapper) wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-primary-subtle border-t-primary" />
          <p className="text-sm text-tx-secondary">Loading PDF...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-danger">{error}</p>
      </div>
    );
  }

  if (!pdf) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-tx-muted">No PDF loaded</p>
      </div>
    );
  }

  const pctLabel = Math.round(scale * 100);

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border bg-card px-3 py-1 shrink-0">
        <div className="flex items-center gap-1 text-xs text-tx-secondary">
          <button onClick={() => scrollToPage(Math.max(1, currentPage - 1))} disabled={currentPage <= 1} className="rounded px-1.5 py-0.5 hover:bg-surface-alt disabled:opacity-30">&#9664;</button>
          <span className="tabular-nums">Page {currentPage} of {numPages}</span>
          <button onClick={() => scrollToPage(Math.min(numPages, currentPage + 1))} disabled={currentPage >= numPages} className="rounded px-1.5 py-0.5 hover:bg-surface-alt disabled:opacity-30">&#9654;</button>
        </div>
        <div className="flex items-center gap-1 text-xs">
          <button onClick={zoomOut} className="rounded px-1.5 py-0.5 text-tx-secondary hover:bg-surface-alt">&minus;</button>
          <span className="tabular-nums text-tx-secondary px-1">{pctLabel}%</span>
          <button onClick={zoomIn} className="rounded px-1.5 py-0.5 text-tx-secondary hover:bg-surface-alt">+</button>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handlePrint} className="rounded px-2 py-0.5 text-xs text-tx-secondary hover:bg-surface-alt">Print</button>
          <button onClick={handleDownload} className="rounded bg-primary px-2 py-0.5 text-xs text-white hover:bg-primary-hover">Download</button>
        </div>
      </div>

      {/* Pages */}
      <div ref={containerRef} className="flex-1 overflow-auto bg-neutral-200 dark:bg-neutral-800 py-2">
        <div className="flex flex-col items-center" style={{ gap: PAGE_GAP }}>
          {Array.from({ length: numPages }, (_, i) => (
            <div
              key={i + 1}
              ref={(el) => {
                if (el) pageRefs.current.set(i + 1, el);
                else pageRefs.current.delete(i + 1);
              }}
              style={{
                backgroundColor: "white",
                boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                // Dimensions set by renderAll / rerender
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
